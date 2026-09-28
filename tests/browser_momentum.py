"""Browser checks. Synthetic fixtures only when MOMENTUM_FIXTURE=1 is explicit."""
import functools
import http.server
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'qa-output'
OUT.mkdir(exist_ok=True)
fixture = os.getenv('MOMENTUM_FIXTURE') == '1'
server = None
base = os.getenv('PAGE_URL', '').rstrip('/')
if not base:
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / 'docs')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
url = base + '/momentum-radar/'
with sync_playwright() as p:
    options = {'headless': True}
    if os.getenv('CHROMIUM_PATH'):
        options['executable_path'] = os.environ['CHROMIUM_PATH']
    browser = p.chromium.launch(**options)
    context = browser.new_context(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True, device_scale_factor=1)
    page = context.new_page(); failures = []
    page.on('pageerror', lambda error: failures.append(str(error)))
    if fixture:
        stamp = datetime.now(timezone.utc).isoformat()
        row = {'symbol':'HBAR-USD','name':'Test Hedera','direction':'LONG','signal':'EINSTIEG','rank':1,'reference_price':.1,'day_pct':2,'m1':1,'m2':2,'m3':3,'stability':70}
        snap = {'version':'momentum-snapshot-1','id':'EXPLICIT-SYNTHETIC-TEST','full_scan':{'generated_at':stamp,'universes':{n:{'coverage':{'with_intraday_data':1,'universe':1},'candidates':{'long':[row],'short':[]}} for n in ('S&P 500','Krypto')}},'watch':{'generated_at':stamp,'base_scan_generated_at':stamp,'candidates':{'HBAR-USD|LONG':{'price':.1,'price_asof':stamp,'ret_15m_pct':1,'ret_30m_pct':1,'ret_60m_pct':1,'watch_signal':'EINSTIEG'}}}}
        page.route('**/snapshot.json?*', lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps(snap)))
    page.goto(url, wait_until='networkidle', timeout=60000)
    page.wait_for_function("document.getElementById('refresh').disabled === false")
    assert page.locator('#universe').count()==1, 'Compact universe selector missing'
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), 'Mobile horizontal overflow'
    assert page.locator('#fetchStatus').inner_text().startswith('Seite geprüft:'), 'Fetch not confirmed'
    ids = page.evaluate('Object.keys(DATA.universes)')
    old_check = page.evaluate('lastFetchAt')
    page.select_option('#universe', ids[-1])
    assert page.evaluate('lastFetchAt') == old_check, 'Render must not falsify last successful fetch time'
    symbol = page.evaluate("DATA.universes[currentUniverse].candidates.long[0]?.symbol || ''")
    if symbol:
        page.fill('#search',symbol)
        assert symbol in page.locator('#longList').inner_text()
        page.fill('#search','')
    page.get_by_text('Depot & Tagesziel – Rechenbeispiel',exact=True).click()
    page.fill('#depot','7200'); page.fill('#allocation','50')
    assert '3.600' in page.locator('#maxUse').inner_text(), 'Capital calculation failed'
    page.reload(wait_until='networkidle')
    assert page.input_value('#depot')=='7200', 'Saved value did not survive reopen'
    assert page.input_value('#universe')==ids[-1], 'Saved universe not restored'
    page.evaluate('window.scrollTo(0,0)')
    page.screenshot(path=str(OUT/'mobile.png'),full_page=True)
    # A failed fetch must block old green signals immediately.
    page.route('**/snapshot.json?*', lambda route: route.fulfill(status=503, body='test'))
    page.click('#refresh');page.wait_for_function("document.getElementById('refresh').disabled === false")
    assert page.locator('#overallSignal').inner_text()=='KEIN EINSTIEG'
    assert page.locator('.candidate.entry').count()==0, 'Old green signal survived fetch failure'
    assert 'Abruf fehlgeschlagen' in page.locator('#fetchStatus').inner_text()
    assert not failures, failures
    evidence={'mode':'synthetic' if fixture else 'live','url':url,'browser':'Chromium mobile emulation','checks':['mobile overflow','load','refresh error','search','universe persistence','depot persistence','last successful fetch timestamp'],'page_errors':failures}
    (OUT/'browser-result.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    browser.close()
if server: server.shutdown()
print(json.dumps(evidence,ensure_ascii=False))
