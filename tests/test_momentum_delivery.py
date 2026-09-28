import copy
import json
import math
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from momentum_delivery import age_minutes, atomic_json, validate_pair
from build_momentum_watch import monitor_signal, frame_for, return_at_minutes, collect_candidates

class Regression(unittest.TestCase):
    def test_age_validation(self):
        now = datetime(2026, 9, 28, 14, tzinfo=timezone.utc)
        self.assertEqual(age_minutes(now.isoformat(), now), 0)
        for bad in (None, 'nonsense', '2026-09-28', (now + timedelta(minutes=2)).isoformat()):
            self.assertTrue(math.isinf(age_minutes(bad, now)))
    def test_reversal_beiersdorf_short(self):
        signal, reason = monitor_signal('EINSTIEG', 'SHORT', 10, .90, 1.21, 1.13, 1.79)
        self.assertEqual(signal, 'KEIN EINSTIEG')
        self.assertIn('Gegenbewegung', reason)
    def test_no_upgrade(self):
        for base in ('KEIN EINSTIEG', 'BEOBACHTEN', 'EINSTIEG'):
            self.assertEqual(monitor_signal(base, 'LONG', 1, 1, 1, 1, 1)[0], base)
    def test_data_gaps_block(self):
        for age, r15 in ((21, 1), (1, None), (1, math.nan)):
            self.assertEqual(monitor_signal('EINSTIEG','LONG',age,r15,1,1,1)[0], 'KEIN EINSTIEG')
    def test_soft_reversal_both_directions(self):
        for direction, change in (('LONG', -.3), ('SHORT', .3)):
            self.assertEqual(monitor_signal('EINSTIEG',direction,1,change,0,0,0)[0], 'BEOBACHTEN')
    def test_complete_bars_only(self):
        raw = pd.DataFrame({'Close': [1., 2., 3.]}, index=pd.to_datetime(['2026-09-28T14:00Z','2026-09-28T14:05Z','2026-09-28T14:06Z']))
        now = datetime(2026,9,28,14,7,tzinfo=timezone.utc)
        self.assertEqual(frame_for(raw, 'X', now, True)['Close'].tolist(), [1.])
        self.assertTrue(frame_for(raw, 'X', now, False).empty)
    def test_multiticker_no_mix(self):
        idx=pd.date_range('2026-09-28T12:00Z',periods=20,freq='5min')
        raw=pd.DataFrame({('Close','A'): range(1,21),('Close','B'): range(21,41)},index=idx)
        now=datetime(2026,9,28,14,tzinfo=timezone.utc)
        self.assertEqual(frame_for(raw,'B',now)['Close'].iloc[-1],40)
    def test_return_not_across_gap(self):
        close=pd.Series([100.,101.],index=pd.to_datetime(['2026-09-25T14:00Z','2026-09-28T14:00Z']))
        self.assertIsNone(return_at_minutes(close,60))
    def test_reference_precision(self):
        row={'symbol':'X-USD','direction':'LONG','price':.12,'reference_price':.117134,'signal':'EINSTIEG'}
        data={'universes':{'Krypto':{'candidates':{'long':[row]}}}}
        self.assertEqual(collect_candidates(data)['X-USD|LONG']['scan_price'],.117134)
        row.pop('reference_price')
        self.assertIsNone(collect_candidates(data)['X-USD|LONG']['scan_price'])
    def test_pair_binding_and_block(self):
        now=datetime.now(timezone.utc); stamp=now.isoformat()
        row={'symbol':'A','direction':'LONG','signal':'BEOBACHTEN'}
        data={'generated_at':stamp,'universes':{'U':{'candidates':{'long':[row]}}}}
        record={'watch_signal':'EINSTIEG','price':100.,'price_asof':stamp,'ret_15m_pct':1.,'ret_30m_pct':1.,'ret_60m_pct':1.}
        watch={'generated_at':stamp,'base_scan_generated_at':stamp,'candidates':{'A|LONG':record}}
        validate_pair(data,watch,now)
        self.assertEqual(record['watch_signal'],'BEOBACHTEN')
        record['price']=None; validate_pair(data,watch,now)
        self.assertEqual(record['watch_signal'],'KEIN EINSTIEG')
        watch['base_scan_generated_at']='wrong'
        with self.assertRaises(ValueError): validate_pair(data,watch,now)
    def test_atomic_json_preserves_previous_on_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.json'; atomic_json(p,{'valid':1})
            with self.assertRaises(ValueError): atomic_json(p,{'invalid':math.nan})
            self.assertEqual(json.loads(p.read_text()),{'valid':1})

if __name__=='__main__': unittest.main()
