from pathlib import Path
import json
from shapely.geometry import Polygon
P=Path(__file__).resolve().parent
source='https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/Arabian_Geology/FeatureServer/0/query?where=1%3D1&outFields=NAME%2COBJECTID&returnGeometry=true&outSR=4326&maxAllowableOffset=0.5&f=geojson'
rows=[]
for line in (P/'data/provinces_source.psv').read_text().splitlines():
 i,en,ar,s=line.split('|');xy=list(map(int,s.split(',')));ring=[[x/100,y/100] for x,y in zip(xy[::2],xy[1::2])];p=Polygon(ring)
 if not p.is_valid: continue
 name=en.lower();kind='volcanic' if 'volcanic' in name else 'shield' if 'shield' in name or 'basement' in name else 'basin' if 'basin' in name or 'trough' in name else 'structure' if any(k in name for k in ['arch','uplift','fold','mountains','belt','graben']) else 'other'
 rows.append(dict(id=int(i),name=ar,en=en,ring=ring,kind=kind,anchor=list(p.representative_point().coords[0])))
v=[]
for line in (P/'data/volcanic_sites.psv').read_text().splitlines():
 i,ar,en,lat,lon,elev,period,last,summary=line.split('|');v.append(dict(id=i,name=ar,en=en,lat=float(lat),lon=float(lon),elevation=int(elev) if elev else None,period=period,last=last,summary=summary,source='https://volcano.si.edu/volcano.cfm?vn='+i))
assert len(rows)==44 and len(v)==12
(P/'data/geology.json').write_text(json.dumps(dict(source=source,reference='https://doi.org/10.3133/ofr97470B',simplification_deg=.5,provinces=rows,volcanoes=v),ensure_ascii=False,separators=(',',':')))
# Spatial join on actual polygon intersection, not interpolated mineral quantities.
import math
from shapely.strtree import STRtree
cm=json.loads((P/'data/cell_metrics.json').read_text()); r=cm['radius']; dy=math.sqrt(3)*r
polys=[Polygon(a['ring']) for a in rows]; tree=STRtree(polys); cell_provinces={}
for c,t,*_ in cm['rows']:
 x=c*1.5*r;y=(t+(c%2)*.5)*dy
 p=Polygon([((x+r*math.cos(i*math.pi/3))*.36-180,90-(y+r*math.sin(i*math.pi/3))*.36) for i in range(6)])
 ids=[rows[k]['id'] for k in tree.query(p,predicate='intersects') if p.intersection(polys[k]).area>0]
 if ids:cell_provinces[f'{c},{t}']=sorted(ids)
d=json.loads((P/'data/geology.json').read_text());d.update(cell_provinces=cell_provinces,excluded=[29]);(P/'data/geology.json').write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')))
print(len(rows),len(v),len(cell_provinces))
