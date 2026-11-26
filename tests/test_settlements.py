import json,hashlib,shutil,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from import_settlements import build,normalize

def test_settlement_data():
 d=json.loads((ROOT/'data/settlements.json').read_text());a=d['records'];assert len(a)==323==len({r['id'] for r in a});assert len({r['region'] for r in a})==13;assert sum(r['rank']==0 for r in a)==13;assert d==build();assert d['rejected']==0
 r,bad=normalize([dict(city_id=1,region_id=7,name_ar='تبوك',name_en='Tabuk',center=[28.4,36.5]),dict(city_id=2,region_id=99,name_ar='X',name_en='X',center=[28,36])]);assert len(r)==1 and bad==1 and r[0]['lon']==36.5
 manifest=json.loads((ROOT/'data/manifest.json').read_text());assert all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in manifest.items())

def test_settlement_browser():
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(10000)
  page.set_content((ROOT/'index.html').read_text(),timeout=40000);assert not errors,errors
  assert page.locator('.settle-point').count()==0
  page.locator('#settlementLaunch').click();assert page.locator('#settlementCount').inner_text()=='323';assert page.locator('[data-settlement-bin]').count()>10;assert page.locator('.settle-cluster').count()>5
  page.screenshot(path=str(ROOT/'docs/geography-preview.png'))
  page.locator('#showlayers').click();page.locator('#settlementRegion').select_option('2');assert page.locator('#settlementCount').inner_text()=='25';page.locator('#settlementFit').click();page.locator('#showlayers').click();page.screenshot(path=str(ROOT/'docs/geography-makkah.png'))
  page.locator('#search').fill('جدة');assert page.locator('#settlementCount').inner_text()=='1';page.locator('#results [data-settlement="18"]').click();assert page.locator('#reader h1').inner_text()=='جدة';assert 'الجغرافيا السعودية المعاصرة' in page.locator('#reader').inner_text();assert 'homaily' in page.locator('#reader .sources a').get_attribute('href');page.screenshot(path=str(ROOT/'docs/geography-jeddah.png'))
  page.locator('[data-era=ancient]').click();assert page.locator('#settlementCount').inner_text()=='0';assert page.locator('.settle-point,.settle-cluster').count()==0;assert page.locator('#mapstyle').input_value()=='hex'
  page.locator('#settlementLaunch').click();page.locator('#showlayers').click() if page.locator('#showlayers').get_attribute('aria-expanded')=='false' else None;page.locator('#settlementRank').select_option('0');assert page.locator('#settlementCount').inner_text()=='13';page.locator('#physicalToggle').check();assert page.locator('#physicalResults button').count()==12
  page.locator('#physicalResults button').filter(has_text='الربع الخالي').click();assert page.locator('#reader h1').inner_text()=='الربع الخالي';page.screenshot(path=str(ROOT/'docs/geography-physical.png'))
  page.locator('#snapshotSelect').select_option('800');assert page.locator('.settle-point,.settle-cluster').count()==0;assert not errors,errors;b.close()

def test_local_import_browser(tmp_path):
 d=json.loads((ROOT/'data/settlements.json').read_text());a=d['records'];src=tmp_path/'cities.json';src.write_text(json.dumps([dict(city_id=r['id'],region_id=r['region'],name_ar=r['name'],name_en=r['en'],center=[r['lat'],r['lon']]) for r in a[:30]]+[dict(city_id=999999,region_id=99,name_ar='invalid',name_en='invalid',center=[25,45])],ensure_ascii=False));bad=tmp_path/'bad.json';bad.write_text('{bad')
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(10000);page.set_content((ROOT/'index.html').read_text(),timeout=40000)
  page.locator('#settlementLaunch').click();page.locator('#showlayers').click();page.locator('details').filter(has_text='توسيع خريطة المواضع').locator('summary').click();page.locator('#settlementImport').set_input_files(str(src));page.wait_for_function("document.getElementById('settlementCount').textContent==='30'");assert '1 سجل' in page.locator('#settlementImportStatus').inner_text();page.locator('#settlementImport').set_input_files(str(bad));page.wait_for_function("document.getElementById('settlementImportStatus').textContent.includes('تعذر الاستيراد')");assert page.locator('#settlementCount').inner_text()=='30';page.locator('#settlementRestore').click();assert page.locator('#settlementCount').inner_text()=='323';assert not errors,errors;b.close()
