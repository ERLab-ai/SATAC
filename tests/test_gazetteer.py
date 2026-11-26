import json,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def test_gazetteer_data():
 records=json.loads((ROOT/'data/gazetteer.json').read_text());stories=json.loads((ROOT/'data/gazetteer_stories.json').read_text());assert len(records)==190 and len({r['id'] for r in records})==190
 assert all(-180<=r['lon']<=180 and -90<=r['lat']<=90 and r['source_certainty'] in {'certain','not_stated'} for r in records)
 assert len(stories)==5 and set(stories)<={r['id'] for r in records};assert all(len(s['sections'])==2 and s['sources'] for s in stories.values())
def test_gazetteer_browser():
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(10000)
  page.set_content((ROOT/'index.html').read_text(),timeout=30000);assert page.locator('.gaz-point').count()>35;assert '190' in page.locator('#mapnotice').inner_text();page.screenshot(path=str(ROOT/'docs/preview.png'))
  page.locator('[data-mapmode=gazetteer]').click();assert page.locator('.gaz-cell').count()>100;page.screenshot(path=str(ROOT/'docs/historical-lens.png'))
  page.locator('[data-era=ancient]').click();assert page.locator('.gaz-point').count()==0 and page.locator('.gaz-cell').count()==0
  page.locator('[data-era=islamic]').click();assert page.locator('.gaz-point').count()>35
  page.locator('[data-mapmode=hex]').click();page.locator('#showlayers').click();page.locator('[data-gaz-kind=waystations]').uncheck();assert not page.locator('[data-gaz-point="RABADHA_413E246N_S"]').count();page.locator('[data-gaz-kind=waystations]').check();page.locator('#gazToggle').uncheck();assert not page.locator('.gaz-point').count();page.locator('#gazToggle').check();page.locator('#showlayers').click()
  page.locator('#search').fill('فيد');assert page.locator('[data-gaz]').count()==1;page.locator('[data-gaz-point="FAYD_425E270N_S"]').click();assert 'فيد' in page.locator('#reader h1').inner_text();assert 'هندسة الماء' in page.locator('#reader').inner_text();assert page.locator('#reader .sources a').count()==3;page.screenshot(path=str(ROOT/'docs/historical-place.png'))
  assert not errors,errors;b.close()
