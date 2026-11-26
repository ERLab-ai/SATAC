import json, hashlib, shutil, math
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'data/encyclopedia.json').read_text())
H=json.loads((ROOT/'data/worldtiles.json').read_text())
ARTICLES={a['id']:a for a in D['articles']}
LEGACY_LINK_TYPES=['حضارة وتراث','الهجرة','الحج والمعرفة','الحج والمعرفة','التجارة والتبادل','الحج والمعرفة','التجارة والتبادل','العلاقات الدولية']

def expected_ids(era='all', excluded=()):
 return {a['id'] for a in D['articles'] if a['category'] not in excluded and (era=='all' or era in a['eras'])}

def expected_links(ids, era='all', excluded=()):
 return {str(i) for i,(a,b,label,*typ) in enumerate(D['links']) if a in ids and b in ids and (typ[0] if typ else LEGACY_LINK_TYPES[i]) not in excluded and (era=='all' or era in ARTICLES[a]['eras'] and era in ARTICLES[b]['eras'])}

def assert_rendered(page, era='all', excluded=(), excluded_links=()):
 ids=expected_ids(era,excluded)
 assert set(page.locator('#points .pin').evaluate_all("els=>els.map(e=>e.dataset.id)"))==ids
 assert page.locator('#points .pin').count()==len(ids)
 links=expected_links(ids,era,excluded_links)
 assert set(page.locator('#connections [data-link]').evaluate_all("els=>els.map(e=>e.dataset.link)"))==links
 assert page.locator('#connections [data-link]').count()==len(links)

def density_count(era='all'):
 r=H['radius']; cells=set()
 for i in expected_ids(era):
  lon,lat=ARTICLES[i]['location']; x=(lon+180)*1000/360; y=(90-lat)*500/180
  c=math.floor(x/(1.5*r)+.5); row=math.floor(y/(math.sqrt(3)*r)-(c%2)*.5+.5)
  cells.add((c,row))
 return len(cells)

def test_data():
 ids=set(ARTICLES);assert len(ids)==len(D['articles']);assert {'jeddah','faw','hima','hegra','petra','makkah'}<=ids
 for a in D['articles']:
  assert a['sources'] and all(s in D['sources'] for s in a['sources']);assert all(r in ids for r in a['related']);assert len(a['sections'])>=2
  assert -180<=a['location'][0]<=180 and -90<=a['location'][1]<=90
 for a,b,c,*typ in D['links']:assert a in ids and b in ids and c and (not typ or len(typ)==1 and typ[0])
 for j in D['journeys']:assert all(i in ids for i in j['ids'])
 for p,h in json.loads((ROOT/'data/manifest.json').read_text()).items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h

def test_browser():
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1000});errors=[];page.set_default_timeout(5000);page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content((ROOT/'index.html').read_text());page.wait_for_selector('.pin',state='attached');assert_rendered(page)
  page.screenshot(path=str(ROOT/'docs/preview.png'))
  page.locator('#showlayers').click();page.locator('[data-layer="الآثار"]').uncheck();assert_rendered(page,excluded=('الآثار',));page.locator('[data-layer="الحضارات"]').uncheck();assert_rendered(page,excluded=('الآثار','الحضارات'));page.locator('#resetlayers').click();assert_rendered(page)
  page.locator('[data-rlayer="التجارة والتبادل"]').uncheck();assert_rendered(page,excluded_links=('التجارة والتبادل',));page.locator('#resetlayers').click()
  page.locator('[data-era=deep]').click();assert_rendered(page,era='deep')
  page.locator('[data-era=all]').click();page.locator('#search').fill('جدة');assert page.locator('.pin').count()>0;page.locator('#search').fill('')
  page.locator('#results [data-open=jeddah]').click();assert 'جدة' in page.locator('#reader h1').inner_text();assert page.locator('#map').is_visible();assert page.locator('#reader .sources a').count()==len(ARTICLES['jeddah']['sources'])
  page.locator('#reader [data-edge="5"]').click();assert 'الحج والمعرفة' in page.locator('#reader h1').inner_text();assert page.locator('.edge.selected').count()==1;page.screenshot(path=str(ROOT/'docs/article.png'))
  page.locator('#discover').click();page.locator('[data-journey="0"]').click();assert 'الفاو' in page.locator('#reader h1').inner_text();page.locator('[data-jnext]').click();assert 'حِمى' in page.locator('#reader h1').inner_text();assert page.locator('#map').is_visible()
  page.locator('#expand').click();assert not page.locator('#reader').is_visible();page.locator('#showreader').click();assert page.locator('#reader').is_visible();page.locator('#showreader').click();page.locator('#world').click();assert page.locator('#map').get_attribute('viewBox')=='0 0 1000 500';page.locator('#zoomplus').click();assert page.locator('#map').get_attribute('viewBox')!='0 0 1000 500'
  page.locator('[data-era=ancient]').click();page.locator('#next').click();assert page.locator('[data-era=islamic]').get_attribute('aria-pressed')=='true';assert not errors,errors
  m=b.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);m.set_content((ROOT/'index.html').read_text());m.wait_for_selector('.pin',state='attached');assert m.locator('#map').is_visible();assert m.evaluate('document.documentElement.scrollWidth<=window.innerWidth');m.screenshot(path=str(ROOT/'docs/mobile.png'));b.close()


def test_geography():
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1000});errors=[];page.set_default_timeout(5000);page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content((ROOT/'index.html').read_text());page.wait_for_selector('#terrain',state='visible');assert page.locator('#terrain').get_attribute('href').startswith('data:image/webp');assert page.locator('.geolabel').count()>10;assert page.locator('#borders').evaluate("el=>el.style.display")=='none'
  page.locator('#showlayers').click();page.locator('#geoBorders').check();assert page.locator('#borders').evaluate("el=>el.style.display")!='none'
  page.locator('#geoRivers').uncheck();assert page.locator('#rivers').evaluate("el=>el.style.display")=='none';page.locator('#geoRivers').check()
  page.locator('#geoLabels').uncheck();assert page.locator('#geonames').evaluate("el=>el.style.display")=='none';page.locator('#geoLabels').check()
  page.locator('#showlayers').click();page.locator('#mapstyle').select_option('etopo');page.screenshot(path=str(ROOT/'docs/elevation.png'));page.locator('#mapstyle').select_option('flat');assert page.locator('#terrain').evaluate("el=>el.style.display")=='none'
  page.locator('#mapstyle').select_option('relief');page.locator('#showlayers').click();page.locator('#geoBorders').uncheck();page.locator('#showlayers').click();page.locator('#zoomplus').click();page.locator('#zoomplus').click();page.screenshot(path=str(ROOT/'docs/detail.png'));page.locator('#world').click();page.screenshot(path=str(ROOT/'docs/world.png'));assert not errors,errors;b.close()


def test_world_rendering():
 H=json.loads((ROOT/'data/worldtiles.json').read_text());assert H['count']==37209 and H['landCount']==23952 and H['texture'].startswith('data:image/webp')
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':900});errors=[];page.set_default_timeout(5000);page.on('pageerror',lambda e:errors.append(str(e)));page.set_content((ROOT/'index.html').read_text());page.wait_for_selector('.pin',state='attached');assert page.locator('#hexworld path').count()==len(H['paths']);assert page.locator('#hextexture').is_visible();assert page.locator('#map').evaluate('el=>el.getBoundingClientRect().width')>=1400;assert not page.locator('#reader').is_visible();page.screenshot(path=str(ROOT/'docs/preview.png'))
  page.locator('[data-mapmode=density]').click();assert page.locator('#densitycells polygon').count()==density_count();page.screenshot(path=str(ROOT/'docs/density.png'));page.locator('[data-era=deep]').click();assert page.locator('#densitycells polygon').count()==density_count('deep')<density_count();page.locator('[data-era=all]').click();page.locator('[data-mapmode=hex]').click();page.locator('#points [data-id=jeddah]').click();assert page.locator('#reader').is_visible();assert 'جدة' in page.locator('#reader h1').inner_text();page.screenshot(path=str(ROOT/'docs/article.png'));page.locator('#showreader').click();page.locator('#showlayers').click();assert page.locator('.controls').is_visible();page.screenshot(path=str(ROOT/'docs/layers.png'));page.locator('#showlayers').click();page.locator('#world').click();assert not page.locator('#hexworld').is_visible();page.locator('#region').click();assert page.locator('#hexworld').is_visible();assert not errors,errors;b.close()
