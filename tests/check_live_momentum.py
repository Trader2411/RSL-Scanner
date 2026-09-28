"""Integration evidence from a real provider call. Never manufacture market data."""
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from momentum_delivery import age_minutes, finite, WATCH_LIMIT, FULL_LIMIT, QUOTE_LIMIT

snapshot = json.loads((ROOT / 'docs/momentum-radar/snapshot.json').read_text())
full, watch = snapshot['full_scan'], snapshot['watch']
now = datetime.now(timezone.utc)
assert not snapshot['health']['errors'], snapshot['health']['errors']
assert age_minutes(full['generated_at'], now) <= FULL_LIMIT
assert age_minutes(watch['generated_at'], now) <= WATCH_LIMIT
assert watch['base_scan_generated_at'] == full['generated_at']
assert len(watch['candidates']) > 0
fresh_records = {key for key, row in watch['candidates'].items()
                 if finite(row.get('price')) and row['price'] > 0
                 and age_minutes(row.get('price_asof'), now) <= QUOTE_LIMIT
                 and all(finite(row.get(field)) for field in ('ret_15m_pct', 'ret_30m_pct', 'ret_60m_pct'))}
usable = {}
for name, universe in full['universes'].items():
    usable[name] = 0
    for side in ('long', 'short'):
        for row in universe['candidates'][side]:
            assert isinstance(row.get('data_quality_ok'), bool)
            if row['data_quality_ok'] and f"{row['symbol']}|{row['direction']}" in fresh_records:
                usable[name] += 1
            if row['signal'] == 'EINSTIEG':
                assert row['data_quality_ok'] is True
                assert row.get('price_asof')
assert fresh_records, 'No fresh, complete candidate quotes received'
assert sum(usable.values()) > 0, 'No full-scan candidate has a valid fresh follow-up quote'
evidence = {
    'mode': 'real-provider-integration', 'snapshot_id': snapshot['id'],
    'full_scan': full['generated_at'], 'watch': watch['generated_at'],
    'coverage': {name: universe['coverage'] for name, universe in full['universes'].items()},
    'watch_records': len(watch['candidates']),
    'priced_watch_records': sum(row.get('price') is not None for row in watch['candidates'].values()),
    'fresh_complete_watch_records': len(fresh_records),
    'usable_candidates_by_universe': usable,
    'entry_watch_records': sum(row.get('watch_signal') == 'EINSTIEG' for row in watch['candidates'].values()),
    'errors': snapshot['health']['errors'],
    'scope': 'One actual run; neither schedule reliability nor profitability verified.'
}
out = ROOT / 'qa-output'
out.mkdir(exist_ok=True)
(out / 'real-provider-result.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
print(json.dumps(evidence, ensure_ascii=False))
