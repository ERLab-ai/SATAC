"""Check the selected simplified geometry against a downloaded original TopoJSON.
Usage: python verify_source_routes.py /path/to/all_routes_new.topojson
No network access required. Exits nonzero on a mismatch.
"""
import json, sys, math
from pathlib import Path
P=Path(__file__).parent
source=json.loads(Path(sys.argv[1]).read_text()); rows=json.loads((P/'data/routes.json').read_text());
scale=source['transform']['scale']; translate=source['transform']['translate']
lookup={g['properties']['id'][:6]:g for g in source['objects']['collection']['geometries']}
def arc(i):
    x=y=0; out=[]
    for dx,dy in source['arcs'][i if i>=0 else ~i]:
        x+=dx;y+=dy;out.append((math.floor((x*scale[0]+translate[0])*100+.5),math.floor((y*scale[1]+translate[1])*100+.5)))
    return out if i>=0 else out[::-1]
def simp(p):
    if len(p)<3:return p
    a,b=p[0],p[-1];dx=b[0]-a[0];dy=b[1]-a[1];l=dx*dx+dy*dy;best=0;k=0
    for i,q in enumerate(p[1:-1],1):
        t=max(0,min(1,((q[0]-a[0])*dx+(q[1]-a[1])*dy)/l)) if l else 0
        d=math.hypot(q[0]-a[0]-t*dx,q[1]-a[1]-t*dy)
        if d>best:best=d;k=i
    return simp(p[:k+1])[:-1]+simp(p[k:]) if best>3 else [a,b]
for r in rows:
    g=lookup[r['id']];a=g['properties']; assert (a['sToponym'],a['eToponym'],a['Meter'])==(r['from_id'],r['to_id'],r['meters']),r['id']
    coords=[list((x/100,y/100)) for x,y in simp([p for i in g['arcs'] for p in arc(i)])]
    assert coords==r['coordinates'],r['id']
print(f'{len(rows)} records match selected source and simplification')
