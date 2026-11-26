import json,math,shutil,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def test_cell_data():
 d=json.loads((ROOT/'data/cell_metrics.json').read_text());a=d['rows'];assert len(a)==2480==len({(x[0],x[1]) for x in a});assert sum(x[3]>0 for x in a)==251;assert all(0<x[2]<3000 and x[3]>=0 for x in a);assert abs(sum(x[3] for x in a)-11807.8)<.2
 h=json.loads((ROOT/'data/worldtiles.json').read_text());r=h['radius'];dy=math.sqrt(3)*r;keys={(round(x/(1.5*r)),round(y/dy-(round(x/(1.5*r))%2)*.5)) for x,y,k in h['land']};assert all(tuple(x[:2]) in keys for x in a)
 m=json.loads((ROOT/'data/manifest.json').read_text());assert all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in m.items())
def test_cells_browser():
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(10000);page.set_content((ROOT/'index.html').read_text(),timeout=40000);assert not errors,errors
  page.locator('#cellLaunch').click();assert page.locator('.metric-cell').count()>=2;assert 'المجاري' in page.locator('#cellKey').inner_text();page.locator('#showlayers').click();page.screenshot(path=str(ROOT/'docs/resources-water.png'))
  # choose a cell through a real mouse click in the visible map, avoiding occupied markers.
  xy=page.evaluate('''()=>{let a=CM.rows.find(a=>{let [x,y]=centerCell(a);return a[3]>0&&x>box[0]+box[2]*.35&&x<box[0]+box[2]*.65&&y>box[1]+box[3]*.3&&y<box[1]+box[3]*.6&&!cellStats.has(a[0]+','+a[1])});if(!a)return null;let [x,y]=centerCell(a),p=new DOMPoint(x,y).matrixTransform(svg.getScreenCTM());return [p.x,p.y]}''');assert xy;page.mouse.click(*xy);assert page.locator('[data-selected-cell]').count()==1;assert 'استكشف هذه المنطقة' in page.locator('#reader h1').inner_text();page.screenshot(path=str(ROOT/'docs/resources-cell.png'))
  page.locator('#showreader').click();page.locator('#showlayers').click();page.locator('#cellMetric').select_option('modern');assert page.locator('#settlementCount').inner_text()=='323';assert 'المواضع المعاصرة' in page.locator('#cellKey').inner_text();page.locator('[data-era=ancient]').click();assert 'المجاري' in page.locator('#cellKey').inner_text();assert page.locator('#settlementCount').inner_text()=='0'
  page.locator('#geoSiteList [data-geosite-open=salma]').click();assert page.locator('#reader h1').inner_text()=='منتزه سلمى الجيولوجي';assert '740' in page.locator('#reader').inner_text();assert page.locator('[data-geosite=salma]').count()==1;page.locator('#showlayers').click();page.screenshot(path=str(ROOT/'docs/resources-geosite.png'));page.locator('[data-era=ancient]').click();assert page.locator('.geosite-point').count()==0;assert not errors,errors;b.close()
