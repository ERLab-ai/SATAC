"""Merge historical gazetteer by canonical place ID. Optional full local CSV; no network dependency."""
from pathlib import Path
import argparse, csv, json, math
P=Path(__file__).resolve().parent
KINDS=dict(zip('trvwscmp',['towns','regions','villages','waters','sites','capitals','metropoles','waystations']))
REGIONS={'JAZI':'Jazirat al-Arab','BADI':'Badiyat al-Arab','YEME':'Yemen'}
SOURCE='https://github.com/althurayya/althurayya.github.io/blob/master/experimental/Data/cornuFiltered.csv'
SHA='525892ec405fbe99e6fbf1293a94072e448a3bcd'

def record(uri,name,lon,lat,kind,region):
    if not uri or not name or kind not in KINDS.values() or not (-180<=lon<=180 and -90<=lat<=90): return None
    parts=uri.split('_')
    if len(parts)!=4: return None
    return dict(id='_'.join(parts[:3]),name=name,lon=lon,lat=lat,region=region,kind=kind,source_certainty='not_stated',source_uri=uri,source_url=SOURCE,source_blob_sha=SHA)

def merge(full=None):
    base=json.loads((P/'data/gazetteer_verified.json').read_text())
    records={a['id']:a for a in base}
    for line in (P/'data/cornu_regional_sample.psv').read_text().splitlines():
        uri,name,x,y,k=line.split('|');a=record(uri,name,int(x)/10000,int(y)/10000,KINDS[k],REGIONS[uri.split('_')[-1]])
        if a: records.setdefault(a['id'],a)
    for line in (P/'data/cornu_global_sample.psv').read_text().splitlines():
        uri,name,x,y,k,region=line.split('|');a=record(uri,name,int(x)/10000,int(y)/10000,KINDS[k],region)
        if a: records.setdefault(a['id'],a)
    if full:
        import hashlib
        raw=Path(full).read_bytes();git_sha=hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
        with open(full,encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                try: a=record(row['topURI'],row['arTitle'],float(row['lon']),float(row['lat']),row['topType'],row['region'])
                except (ValueError,KeyError,TypeError): continue
                if a:
                    a['source_blob_sha']=git_sha
                    records.setdefault(a['id'],a)
    return list(records.values())
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--csv',help='Optional full Cornu CSV downloaded from the documented source');args=p.parse_args()
    data=merge(args.csv);(P/'data/gazetteer.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));print(f'{len(data)} records')
