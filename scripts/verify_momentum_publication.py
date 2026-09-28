"""Prove that Pages actually serves the committed snapshot, not just an old file."""
import json
import os
import time
import urllib.request
from pathlib import Path

path=Path('docs/momentum-radar/snapshot.json')
if not path.exists():
    print('NO_SNAPSHOT_YET: UI deployment only; no market-data success claim.')
    raise SystemExit(0)
expected=json.loads(path.read_text(encoding='utf-8'))
url=os.environ['PAGE_URL'].rstrip('/')+'/momentum-radar/snapshot.json'
for attempt in range(8):
    try:
        request=urllib.request.Request(url+'?verify='+str(time.time_ns()),headers={'Cache-Control':'no-cache','User-Agent':'MomentumRadar-QA'})
        with urllib.request.urlopen(request,timeout=20) as response:
            actual=json.load(response)
        if actual.get('id')!=expected['id']:
            raise ValueError('Pages is not serving the intended snapshot')
        assert actual['watch']['base_scan_generated_at']==actual['full_scan']['generated_at']
        result={'snapshot_id':actual['id'],'full_scan':actual['full_scan'].get('generated_at'),
                'watch':actual['watch'].get('generated_at'),'trigger':actual['health'].get('trigger'),
                'candidates':len(actual['watch'].get('candidates',{})),'errors':actual['health'].get('errors',[])}
        print('PAGES_VERIFIED '+json.dumps(result))
        if os.getenv('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as stream:
                stream.write('## Pages delivery verified\n```json\n'+json.dumps(result,indent=2)+'\n```\n')
        if result['errors']:
            raise RuntimeError('Published error state, not healthy market data')
        break
    except Exception as exc:
        print(f'Publication check {attempt+1}/8: {type(exc).__name__}: {exc}')
        if attempt==7: raise
        time.sleep(5)
