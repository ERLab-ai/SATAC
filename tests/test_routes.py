import json, hashlib, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def test_routes_data():
    data=json.loads((ROOT/'data/routes.json').read_text())
    assert len(data)==145 and len(set(x['id'] for x in data))==145
    assert all(x['meters']>0 and len(x['coordinates'])>=2 and all(-180<=lon<=180 and -90<=lat<=90 for lon,lat in x['coordinates']) for x in data)
    assert len({x[k] for x in data for k in ['from_id','to_id']})>100
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in manifest.items())
def test_routes_browser():
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(15000)
        page.set_content((ROOT/'index.html').read_text(),timeout=30000)
        assert page.locator('.route-piece').count()>90
        assert '145' in page.locator('#mapnotice').inner_text()
        page.screenshot(path=str(ROOT/'docs/preview.png'))
        page.locator('[data-era=ancient]').click();assert page.locator('.route-piece').count()==0
        page.locator('[data-era=islamic]').click();assert page.locator('.route-piece').count()>90
        page.locator('#routeTool').click();assert 'شبكة الطرق' in page.locator('#reader h1').inner_text()
        page.locator('#routeForm button').click();assert page.locator('.route-piece.onpath').count()==2
        assert 'مكة' in page.locator('#routeAnswer').inner_text();assert '71' in page.locator('#routeAnswer').inner_text() or '٧١' in page.locator('#routeAnswer').inner_text()
        page.screenshot(path=str(ROOT/'docs/route-journey.png'))
        page.locator('#routeFrom').select_option('NAJAF_443E319N_S_IRAQ');page.locator('#routeTo').select_option('MAKKA_398E213N_S_JAZI');page.locator('#routeForm button').click();assert page.locator('.route-piece.onpath').count()>20;page.screenshot(path=str(ROOT/'docs/route-long.png'))
        page.locator('#routeAnswer button[data-route-segment]:not([disabled])').first.click();assert 'كم' in page.locator('#reader').inner_text();assert page.locator('#reader .sources a').count()==3
        page.locator('#showreader').click();page.locator('#showlayers').click();page.locator('#routeToggle').uncheck();assert page.locator('.route-piece').count()==0
        page.locator('#routeToggle').check();assert page.locator('.route-piece').count()>0
        assert not errors,errors;b.close()
