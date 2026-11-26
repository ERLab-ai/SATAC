"""Import the homaily cities.json (lat, lon) as a separate modern reference layer.
No historical dates or population are inferred. The packaged sample is a manual
transfer of selected source records, rounded to 4 decimal places.
"""
import argparse,json,hashlib,math
from pathlib import Path
P=Path(__file__).parent
REGIONS=['','الرياض','مكة المكرمة','المدينة المنورة','القصيم','الشرقية','عسير','تبوك','حائل','الحدود الشمالية','جازان','نجران','الباحة','الجوف']
CAPITALS={3,6,14,11,13,15,1,10,2213,17,3417,1542,2237}
URL='https://github.com/homaily/Saudi-Arabia-Regions-Cities-and-Districts/blob/master/json/cities.json'
SHA='63fb90f701f855e4afa30d7f4bbf9b18ebff2055'
def normalize(rows, major=()):
    out={}; rejected=0
    for r in rows:
        try:
            i=int(r['city_id']); reg=int(r['region_id']); name=r['name_ar']; en=r['name_en']; lat,lon=map(float,r['center'])
            assert i>0 and 1<=reg<=13 and isinstance(name,str) and name.strip() and isinstance(en,str) and math.isfinite(lat) and math.isfinite(lon) and 15.5<=lat<=33 and 34<=lon<=56.5
        except (KeyError,ValueError,TypeError,AssertionError):
            rejected+=1;continue
        out[i]={'id':i,'region':reg,'name':name,'en':en,'lon':round(lon,4),'lat':round(lat,4),'rank':0 if i in CAPITALS else 1 if i in major else 2}
    return sorted(out.values(),key=lambda r:(r['rank'],r['id'])),rejected

def sample_rows(path):
    for line in path.read_text().splitlines():
        if not line.strip():continue
        i,reg,name,en,lat,lon=line.split('|');yield dict(city_id=int(i),region_id=int(reg),name_ar=name,name_en=en,center=[int(lat)/10000,int(lon)/10000])
def build(path=None):
    a=list(sample_rows(P/'data/saudi_settlements_sample.psv'));b=list(sample_rows(P/'data/saudi_major_sample.psv'))
    major={r['city_id'] for r in b}|{24,5,80,12,62,2208,2268}
    rows=json.loads(path.read_text()) if path else a+b
    out,rejected=normalize(rows,major)
    return {'source':URL,'source_blob_sha':SHA if not path else None,'source_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest() if path else None,'license':'GPL-2.0 (repository license; review before public redistribution)','coverage':'external-import' if path else 'regional-sample','regions':REGIONS,'records':out,'rejected':rejected}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,help='Original cities.json from source');a=p.parse_args();d=build(a.input);(P/'data/settlements.json').write_text(json.dumps(d,ensure_ascii=False,indent=2));print(len(d['records']),d['rejected'])
