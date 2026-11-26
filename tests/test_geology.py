import json,shutil,hashlib
from pathlib import Path
from shapely.geometry import Polygon
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def test_geology_data():
 d=json.loads((ROOT/'data/geology.json').read_text()); assert len(d['provinces'])==44 and len(d['volcanoes'])==12 and d['excluded']==[29];assert len(d['cell_provinces'])==1847
 ids={p['id'] for p in d['provinces']};assert ids==set(range(1,46))-{29};assert all(Polygon(p['ring']).is_valid for p in d['provinces']);assert all(set(a)<=ids for a in d['cell_provinces'].values());assert sum(v['period']=='holocene' for v in d['volcanoes'])==8;assert all(v['source'].endswith(v['id']) for v in d['volcanoes']);m=json.loads((ROOT/'data/manifest.json').read_text());assert all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in m.items())
def test_geology_browser():
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(12000);page.set_content((ROOT/'index.html').read_text(),timeout=40000);assert not errors,errors
  page.locator('#geologyLaunch').click();assert page.locator('.geology-province').count()==44;assert page.locator('.volcano-point').count()==12;page.locator('#showlayers').click();page.screenshot(path=str(ROOT/'docs/geology-preview.png'))
  xy=page.evaluate('''()=>{let a=provinceById.get(23),r=svg.getBoundingClientRect();let [x,y]=project(...a.anchor),p=new DOMPoint(x,y).matrixTransform(svg.getScreenCTM());for(let i=-40;i<=40;i+=10)for(let j=-30;j<=30;j+=10){let el=document.elementFromPoint(p.x+i,p.y+j);if(el?.closest('[data-province=\"23\"]'))return [p.x+i,p.y+j]}return null}''');assert xy;page.mouse.click(*xy);assert page.locator('#reader h1').inner_text()=='حوض الربع الخالي';page.locator('#showreader').click()
  page.locator('#showlayers').click();page.locator('#provinceKind').select_option('shield');assert page.locator('.geology-province').count()==4;page.locator('#volcanoPeriod').select_option('pleistocene');assert page.locator('.volcano-point').count()==4;page.locator('#volcanoPeriod').select_option('all');page.locator('#provinceKind').select_option('all')
  page.locator('details').filter(has_text='استكشف الأقاليم والحرات').locator('summary').click();page.locator('#geologyList [data-province-open="17"]').click();assert page.locator('#reader h1').inner_text()=='الدرع العربي';assert 'USGS' in page.locator('#reader').inner_text();page.locator('#showlayers').click();page.screenshot(path=str(ROOT/'docs/geology-shield.png'))
  page.locator('#search').fill('حرة رهط');page.locator('#results [data-volcano-open="231070"]').click();assert page.locator('#reader h1').inner_text()=='حرة رهط';assert '1256' in page.locator('#reader').inner_text();page.screenshot(path=str(ROOT/'docs/geology-rahat.png'));page.locator('#search').fill('')
  page.locator('[data-era=ancient]').click();assert page.locator('.volcano-point').count()==12;assert 'مرجعية' in page.locator('#geologyKey').inner_text()
  page.locator('#cellLaunch').click();page.evaluate('''()=>{let a=CM.rows.find(a=>GL.cell_provinces[a[0]+','+a[1]]?.includes(17));chooseCell(a)}''');assert page.locator('#reader [data-province-open="17"]').count()==1;assert not errors,errors;b.close()
