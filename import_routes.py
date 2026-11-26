from pathlib import Path
import json,csv
p=Path(__file__).parent
rows=[]
for sid,a,b,m,coords in csv.reader((p/'data/routes_sample.tsv').open(),delimiter='|'):
    c=[int(x)/100 for x in coords.split(',')]
    assert len(c)>=4 and len(c)%2==0
    rows.append(dict(id='CR'+sid,from_id=a,to_id=b,meters=int(m),coordinates=[c[i:i+2] for i in range(0,len(c),2)]))
assert len({x['id'] for x in rows})==len(rows)
(p/'data/routes.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
