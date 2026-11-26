import json, hashlib, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'data/encyclopedia.json').read_text())
def test_heritage_data():
    a=json.loads((ROOT/'data/heritage_additions.json').read_text()); ids={x['id'] for x in D['articles']}
    assert len(a)==32 and len(ids)==len(D['articles'])==50
    assert len({x['id'] for x in a})==32
    assert all(x['sources'] and all(k in D['sources'] for k in x['sources']) and all(r in ids for r in x['related']) for x in D['articles'])
    assert all(-180<=x['location'][0]<=180 and -90<=x['location'][1]<=90 for x in a)
    assert all(l[0] in ids and l[1] in ids for l in D['links'])
    assert all(i in ids for j in D['journeys'] for i in j['ids'])
    assert sum(x['heritage_status']=='مدرج في قائمة التراث العالمي' for x in a)==2
    assert len(D['links'])==13 and len(D['journeys'])==8
    manifest=json.loads((ROOT/'data/manifest.json').read_text()); assert all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in manifest.items())
def test_heritage_browser():
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(15000)
        page.set_content((ROOT/'index.html').read_text(),timeout=40000)
        assert page.locator('.pin').count()==50 and page.locator('[data-link]').count()==13
        page.screenshot(path=str(ROOT/'docs/heritage-preview.png'))
        page.locator('[data-era=deep]').click();assert page.locator('[data-id=stones_rajajil]').count()==1 and page.locator('[data-id=oil_well]').count()==0
        page.locator('#showlayers').click();page.locator('[data-layer="المنشآت الحجرية"]').uncheck();assert page.locator('[data-id=stones_rajajil]').count()==0;page.locator('[data-layer="المنشآت الحجرية"]').check();page.locator('#showlayers').click()
        page.screenshot(path=str(ROOT/'docs/heritage-deep.png'))
        page.locator('[data-era=all]').click();page.locator('#search').fill('سد الخنق');page.locator('[data-open=dam_khanaq]').first.click();assert 'سد الخنق' in page.locator('#reader h1').inner_text();assert 'معاوية' in page.locator('#reader').inner_text();assert '6637' in page.locator('#reader .sources a').first.get_attribute('href')
        page.screenshot(path=str(ROOT/'docs/heritage-dam.png'))
        page.locator('#search').fill('تيماء');page.locator('[data-open=oasis_tayma]').first.click();page.locator('#reader [data-edge="8"]').click();assert 'نابونيد' in page.locator('#reader h1').inner_text();assert page.locator('.edge.selected').count()==1
        page.screenshot(path=str(ROOT/'docs/heritage-babylon.png'))
        page.locator('[data-era=modern]').click();assert page.locator('[data-id=oil_tapline]').count()==1 and page.locator('[data-id=stones_rajajil]').count()==0
        page.locator('#search').fill('عروق بني معارض');page.locator('[data-open=uruq]').first.click();assert 'مدرج في قائمة التراث العالمي' in page.locator('#reader').inner_text();assert page.locator('#reader .sources a').count()==1
        assert not errors,errors;b.close()
