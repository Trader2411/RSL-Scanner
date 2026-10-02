import copy
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from crypto_history import verified_closes, repair_crypto_prices

NOW = datetime(2026, 10, 2, 6, tzinfo=timezone.utc)
DAY = '2026-10-01'
START = int(datetime(2026, 10, 1, tzinfo=timezone.utc).timestamp())

def fixture():
    return {'chart': {'error': None, 'result': [{'meta': {'symbol': 'BTC-USD', 'currency': 'USD', 'dataGranularity': '1h'}, 'timestamp': list(range(START, START+86400, 3600)), 'indicators': {'quote': [{'close': list(range(100, 124))}]}}]}}

class CryptoHistoryTests(unittest.TestCase):
    def test_complete_closed_day_uses_last_hour_close(self):
        self.assertEqual(verified_closes(fixture(),'BTC-USD',[DAY],NOW), {DAY:123})
    def test_incomplete_duplicate_null_wrong_symbol_and_future_are_rejected(self):
        for kind in ['missing','duplicate','null','negative','symbol','currency','interval']:
            p=fixture();r=p['chart']['result'][0]
            if kind=='missing': r['timestamp'].pop();r['indicators']['quote'][0]['close'].pop()
            if kind=='duplicate': r['timestamp'][-1]=r['timestamp'][-2]
            if kind=='null': r['indicators']['quote'][0]['close'][12]=None
            if kind=='negative': r['indicators']['quote'][0]['close'][12]=-1
            if kind=='symbol': r['meta']['symbol']='ETH-USD'
            if kind=='currency': r['meta']['currency']='EUR'
            if kind=='interval': r['meta']['dataGranularity']='1d'
            self.assertEqual(verified_closes(p,'BTC-USD',[DAY],NOW),{},kind)
        self.assertEqual(verified_closes(fixture(),'BTC-USD',[DAY],datetime(2026,10,2,0,10,tzinfo=timezone.utc)),{})
    def test_only_missing_crypto_day_is_merged_no_existing_close_is_changed(self):
        import pandas as pd
        idx=pd.date_range('2026-02-01','2026-10-02')
        frame=pd.DataFrame({'BTC-USD':200.,'GC=F':300.},index=idx)
        frame.loc[DAY,'BTC-USD']=float('nan')
        calls=[]
        def request(symbol, days):
            calls.append((symbol,days));return fixture()
        repaired, provenance=repair_crypto_prices(frame,['BTC-USD','GC=F'],NOW,request)
        self.assertEqual(repaired.loc[DAY,'BTC-USD'],123)
        self.assertEqual(repaired.loc['2026-09-30','BTC-USD'],200)
        self.assertEqual(repaired.loc[DAY,'GC=F'],300)
        self.assertEqual(provenance,{'BTC-USD':[DAY]})
        self.assertEqual(calls,[('BTC-USD',[DAY])])
        repaired, provenance=repair_crypto_prices(repaired,['BTC-USD'],NOW,lambda *_:self.fail('Unneeded request'))
        self.assertEqual(provenance,{})
    def test_failed_repair_keeps_gap(self):
        import pandas as pd
        frame=pd.DataFrame({'BTC-USD':200.},index=pd.date_range('2026-02-01','2026-10-02'))
        frame.loc[DAY,'BTC-USD']=float('nan')
        repaired, provenance=repair_crypto_prices(frame,['BTC-USD'],NOW,lambda *_:{})
        self.assertTrue(pd.isna(repaired.loc[DAY,'BTC-USD']))
        self.assertEqual(provenance,{})

if __name__=='__main__': unittest.main()
