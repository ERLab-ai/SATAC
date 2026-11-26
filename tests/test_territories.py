import hashlib,json,shutil
from pathlib import Path
from shapely.geometry import shape,Point
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def test_territory_data():
    records=json.loads((ROOT/'data/territories.json').read_text())
    assert len(records)==27 and len({r['id'] for r in records})==27
    assert {r['year'] for r in records}=={-200,600,800,1000,1279}
    for r in records:
        g=shape(r['geometry']); assert g.is_valid and g.area>0
        assert g.distance(Point(r['label']))<.03
        assert r['border_precision']==1 and len(r['source_blob_sha'])==40
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    assert all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h for f,h in manifest.items())
def test_territory_browser():
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(12000)
        page.set_content((ROOT/'index.html').read_text(),timeout=40000)
        assert page.locator('.route-piece').count()>90 and page.locator('.territory-item').count()==0
        page.locator('#territoryTool').click();assert page.locator('.territory-item').count()==3 and page.locator('.route-piece').count()==0
        page.screenshot(path=str(ROOT/'docs/territories-800.png'))
        page.locator('#snapshotSelect').select_option('1000');assert page.locator('.territory-item').count()==7 and page.locator('.route-piece').count()>90
        page.locator('#compareSelect').select_option('800');assert page.locator('.territory-compare').count()==3
        page.screenshot(path=str(ROOT/'docs/territories-compare.png'))
        page.locator('#snapshotSelect').select_option('-200');assert page.locator('.territory-item').count()==4 and page.locator('.route-piece').count()==0
        page.locator('.territory-label').filter(has_text='مملكة الأنباط').click();assert 'الأنباط' in page.locator('#reader h1').inner_text();assert page.locator('#reader .sources a').count()==2
        page.screenshot(path=str(ROOT/'docs/territories-nabataeans.png'))
        page.locator('#snapshotSelect').select_option('1727');assert page.locator('.territory-item').count()==0 and page.locator('.milestone-marker').count()==1 and page.locator('.territory-compare').count()==0
        page.locator('.milestone-marker circle').click();assert 'الدولة السعودية الأولى' in page.locator('#reader h1').inner_text();page.screenshot(path=str(ROOT/'docs/territories-1727.png'))
        page.locator('#snapshotSelect').select_option('1932');assert page.locator('.milestone-marker').count()==1
        page.locator('[data-era=islamic]').click();assert page.locator('.milestone-marker').count()==0 and page.locator('.route-piece').count()>90
        assert not errors,errors;b.close()
