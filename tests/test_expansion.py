import json,shutil,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from import_expansion import merge

def test_merge(tmp_path):
    a=merge(); assert len(a)==190 and len({p['id'] for p in a})==190
    assert len({p['region'] for p in a})==19
    assert sum(p.get('source_uri') is not None for p in a)==136
    assert sum(p['source_certainty']=='certain' for p in a)==54
    assert all(p.get('source_blob_sha') for p in a if p.get('source_uri'))
    f=tmp_path/'test.csv'; f.write_text('topURI,arTitle,lon,lat,topType,region\nMAKKA_398E213N_S_JAZI,duplicate,39,21,towns,Jazirat al-Arab\nTEST_001E001N_S_TEST,اختبار,1,1,towns,Test\nBAD_001E001N_S_TEST,invalid,999,1,towns,Test\n',encoding='utf-8')
    b=merge(f);assert len(b)==191 and next(p for p in b if p['id']=='MAKKA_398E213N_S')['name']=='مكة'

def test_expansion_browser():
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(12000)
        page.set_content((ROOT/'index.html').read_text(),timeout=40000)
        assert '190' in page.locator('#mapnotice').inner_text()
        assert page.locator('.gaz-point').count()>60
        page.screenshot(path=str(ROOT/'docs/expansion-preview.png'))
        page.locator('#showlayers').click();page.locator('#gazRegion').select_option('Andalus');assert page.locator('[data-gaz]').count()==1
        page.locator('#gazFitRegion').click();assert page.locator('[data-gaz-point="QURTUBA_047W379N_S"]').count()==1
        page.screenshot(path=str(ROOT/'docs/expansion-andalus.png'))
        page.locator('#gazRegion').select_option('');page.locator('#showlayers').click();page.locator('#search').fill('دومة الجندل');assert page.locator('[data-gaz]').count()==1
        page.locator('[data-gaz="DAWMAJANDAL_398E297N_S"]').click();assert 'دومة الجندل' in page.locator('#reader h1').inner_text();assert 'cornuFiltered.csv' in page.locator('#reader .sources a').first.get_attribute('href')
        page.screenshot(path=str(ROOT/'docs/expansion-place.png'))
        page.locator('[data-era=ancient]').click();assert page.locator('.gaz-point').count()==0
        assert not errors,errors;b.close()
