"""Browser checks. Synthetic fixtures only when MOMENTUM_FIXTURE=1 is explicit."""
import functools
import copy
import http.server
import json
import os
import threading
from datetime import datetime, timedelta, timezone
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
    context = browser.new_context(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True, device_scale_factor=1, timezone_id='UTC')
    page = context.new_page(); failures = []
    page.on('pageerror', lambda error: failures.append(str(error)))
    if fixture:
        stamp = datetime.now(timezone.utc).isoformat()
        row = {'symbol':'HBAR-USD','name':'Test Hedera','direction':'LONG','signal':'EINSTIEG','rank':1,'score':86,'reference_price':.1,'day_pct':2,'m1':1,'m2':2,'m3':3,'stability':70,'volume_ratio':1,'rel_index':1,'rel_sector':1,'price_asof':stamp,'data_quality_ok':True,'data_quality_issues':[]}
        snap = {'version':'momentum-snapshot-1','id':'EXPLICIT-SYNTHETIC-TEST','generated_at':stamp,'full_scan':{'generated_at':stamp,'universes':{n:{'coverage':{'with_intraday_data':1,'with_quality_data':1,'universe':1},'candidates':{'long':[row],'short':[]}} for n in ('S&P 500','Krypto')}},'watch':{'generated_at':stamp,'base_scan_generated_at':stamp,'candidates':{'HBAR-USD|LONG':{'symbol':'HBAR-USD','direction':'LONG','price':.1,'price_asof':stamp,'ret_15m_pct':1,'ret_30m_pct':1,'ret_60m_pct':1,'watch_signal':'EINSTIEG'}}}}
        page.route('**/snapshot.json?*', lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps(snap)))
    page.goto(url, wait_until='networkidle', timeout=60000)
    page.wait_for_function("document.getElementById('refresh').disabled === false")
    assert page.locator('#universe').count()==1, 'Compact universe selector missing'
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), 'Mobile horizontal overflow'
    assert page.locator('#fetchStatus').inner_text().startswith('Seite geprüft:'), 'Fetch not confirmed'
    assert '(Wien)' in page.locator('#updated').inner_text(), 'Data timezone missing'
    if fixture:
        assert page.locator('#overallSignal').inner_text()=='EINSTIEG', 'Valid fixture signal blocked'
        assert page.locator('#signalSummary').inner_text()=='Einstiege: 1 LONG · 0 SHORT'
        assert page.locator('#recovery').is_hidden(), 'Failure recovery shown with healthy data'
        assert '86 %' in page.locator('#directionStrengths').inner_text(), 'Signal strength missing'
        assert 'Short —' in page.locator('.strength-pair').first.inner_text(), 'Opposite strength invented'
        assert page.locator('.compass-return').get_attribute('href') == 'https://strategiekompass.w-p1.chatgpt.site'
    # Whole overview cards navigate, clear search and open Short directly.
    for side in ('short','long'):
        page.fill('#search','NO_MATCH_EXPECTED')
        page.locator('#'+side+'Strength').click()
        assert page.input_value('#search') == '', 'Overview click left a hidden search filter'
        assert page.locator('#'+side+'Ranking').is_visible()
        assert page.locator('#'+side+'Ranking').bounding_box()['y'] >= page.locator('header').bounding_box()['height'], 'Sticky header covers ranking heading'
        if side == 'short':
            assert page.locator('#shortRanking').get_attribute('open') is not None
        assert page.evaluate('document.activeElement.id') == side+'Ranking', 'Ranking focus missing'
        assert page.locator('#'+side+'List .candidate').count() <= 5
        expected = page.evaluate("side => RadarState.ranked(SNAP,universeData().candidates[side],Date.now(),!!loadError).map(x=>x.symbol)", side)
        actual = page.locator('#'+side+'List .candidate').evaluate_all('(rows)=>rows.map(x=>x.dataset.symbol)')
        assert actual == expected, 'Visible top-five ranking is not sorted'
        page.locator('#'+side+'Back').click()
        assert page.evaluate('document.activeElement.id') == side+'Strength', 'Return to overview failed'
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), 'Ranking causes horizontal overflow'
    ids = page.evaluate('Object.keys(DATA.universes)')
    old_check = page.evaluate('lastFetchAt')
    page.select_option('#universe', ids[-1])
    assert page.evaluate('lastFetchAt') == old_check, 'Render must not falsify last successful fetch time'
    symbol = page.evaluate("DATA.universes[currentUniverse].candidates.long[0]?.symbol || ''")
    if symbol:
        page.fill('#search',symbol)
        assert symbol in page.locator('#longList').inner_text()
        page.fill('#search','')
        page.locator('#longList .candidate details summary').first.click()
        page.evaluate('render()')
        assert page.locator('#longList .candidate details').first.get_attribute('open') is not None, 'Automatic render closed expanded metrics'
    page.get_by_text('Depot & Tagesziel – Rechenbeispiel',exact=True).click()
    page.fill('#depot','7200'); page.fill('#allocation','50')
    assert '3.600' in page.locator('#maxUse').inner_text(), 'Capital calculation failed'
    assert '72' in page.locator('#target1').inner_text(), 'Depot target calculation failed'
    assert '2.0 %' in page.locator('#need1').inner_text(), 'Required return on capital calculation failed'
    page.fill('#allocation','0')
    assert page.locator('#maxUse').inner_text()=='—', 'Invalid allocation silently recalculated'
    assert page.evaluate("localStorage.getItem('momentumRadarAllocation')")=='50', 'Invalid input overwrote valid saved setting'
    page.fill('#allocation','75')
    assert page.locator('#maxUse').inner_text()=='—', 'Allocation above confirmed 50% limit accepted'
    assert 'höchstens 50 %' in page.locator('#targetStatus').inner_text(), 'Allocation cap has no explanation'
    assert page.evaluate("localStorage.getItem('momentumRadarAllocation')")=='50', 'Excess allocation overwrote saved limit'
    page.fill('#allocation','50')
    assert '3.600' in page.locator('#maxUse').inner_text(), 'Restoring permitted allocation did not recover calculation'
    assert '1 % Depotgewinn' in page.locator('#targetStatus').inner_text(), 'Depot versus invested-capital return not explained'
    page.evaluate("localStorage.setItem('momentumRadarAllocation','75')")
    page.reload(wait_until='networkidle')
    page.wait_for_function("document.getElementById('refresh').disabled === false")
    # Reload collapses <details>; open the panel before asserting rendered text.
    page.get_by_text('Depot & Tagesziel – Rechenbeispiel',exact=True).click()
    assert page.input_value('#allocation')=='75', 'Invalid legacy allocation was silently changed'
    assert page.locator('#maxUse').is_visible(), 'Reopened target panel not visible'
    assert page.locator('#maxUse').inner_text()=='—', f"Invalid saved allocation produced a target: {page.locator('#maxUse').text_content()!r}"
    assert 'Höhere gespeicherte Werte sind ungültig.' in page.locator('#targetStatus').inner_text(), 'Invalid saved allocation unexplained'
    page.fill('#allocation','50')
    page.reload(wait_until='networkidle')
    page.wait_for_function("document.getElementById('refresh').disabled === false")
    assert page.input_value('#depot')=='7200', 'Saved value did not survive reopen'
    assert page.input_value('#allocation')=='50', 'Permitted allocation did not survive reopen'
    assert page.input_value('#universe')==ids[-1], 'Saved universe not restored'
    page.evaluate('window.scrollTo(0,0)')
    page.screenshot(path=str(OUT/'mobile.png'),full_page=True)
    # A failed fetch must block old green signals immediately.
    page.route('**/snapshot.json?*', lambda route: route.fulfill(status=503, body='test'))
    page.click('#refresh');page.wait_for_function("document.getElementById('refresh').disabled === false")
    assert page.locator('#overallSignal').inner_text()=='KEIN EINSTIEG'
    assert page.locator('.candidate.entry').count()==0, 'Old green signal survived fetch failure'
    assert '%' not in page.locator('#directionStrengths').inner_text(), 'Old strength survived fetch failure'
    assert 'Abruf fehlgeschlagen' in page.locator('#fetchStatus').inner_text()
    assert page.locator('#recovery').is_visible(), 'Failed fetch offers no existing-workflow recovery'
    if fixture:
        page.route('**/snapshot.json?*', lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps(snap)))
        page.click('#refresh');page.wait_for_function("document.getElementById('refresh').disabled === false")
        assert page.locator('#overallSignal').inner_text()=='EINSTIEG', 'Successful recovery did not restore a valid signal'
        confirmed = page.evaluate('lastFetchAt')
        malformed = copy.deepcopy(snap)
        malformed['full_scan']['universes']['Krypto']['candidates']['long'] = None
        page.route('**/snapshot.json?*', lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps(malformed)))
        page.click('#refresh');page.wait_for_function("document.getElementById('refresh').disabled === false")
        assert page.locator('#overallSignal').inner_text()=='KEIN EINSTIEG', 'Malformed payload left green signal'
        assert page.evaluate('lastFetchAt')==confirmed, 'Malformed payload changed successful-fetch clock'
        assert page.locator('#longList .candidate').count()==1, 'Malformed payload destroyed last known candidates'
        older = copy.deepcopy(snap)
        older['watch']['generated_at'] = (datetime.fromisoformat(stamp)-timedelta(minutes=1)).isoformat()
        page.route('**/snapshot.json?*', lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps(older)))
        page.click('#refresh');page.wait_for_function("document.getElementById('refresh').disabled === false")
        assert page.evaluate('lastFetchAt')==confirmed, 'Older CDN generation replaced newer data'
        assert 'Älteres Datenpaket' in page.locator('#fetchStatus').inner_text(), 'Older generation has no visible explanation'
    assert not failures, failures
    checks=['Long/Short top-five navigation and return','direction ranking and five-row limit','mobile overflow','load','refresh error','search','universe persistence','depot persistence','last successful fetch timestamp','Vienna timezone label','expanded metrics retained','capital and target calculation','invalid setting rejected','existing workflow recovery']
    if fixture: checks += ['green valid fixture','successful refresh recovery','malformed payload rollback','older generation rejected']
    evidence={'mode':'synthetic' if fixture else 'live','url':url,'browser':'Chromium mobile emulation','checks':checks,'page_errors':failures}
    (OUT/'browser-result.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    browser.close()
if server: server.shutdown()
print(json.dumps(evidence,ensure_ascii=False))
