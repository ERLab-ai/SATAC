"""Compute geodesic hex area and clipped mapped watercourse length, from inherited atlas geometry.
Grid is a display grid, not equal-area. No water availability or historic hydrology is inferred.
"""
from pathlib import Path
import json,math,re
from collections import Counter
from shapely.geometry import Polygon,LineString
from shapely.strtree import STRtree
from pyproj import Geod
P=Path(__file__).parent
H=json.loads((P/'data/worldtiles.json').read_text());G=json.loads((P/'data/geography.json').read_text())
r=H['radius'];dy=math.sqrt(3)*r;geod=Geod(ellps='WGS84')
def lonlat(x,y):return x*.36-180,90-y*.36
def length(g):
 if g.is_empty:return 0
 if g.geom_type=='LineString':return geod.line_length(*zip(*(lonlat(x,y) for x,y in g.coords)))/1000
 if hasattr(g,'geoms'):return sum(length(a) for a in g.geoms)
 return 0
lines=[LineString([tuple(map(float,p)) for p in re.findall(r'[ML]([\d.\-]+),([\d.\-]+)',s)]) for s in G['regionalRivers']]
tree=STRtree(lines);rows=[]
for x,y,k in H['land']:
 lon,lat=lonlat(x,y)
 if not(34<=lon<=60 and 12<=lat<=34):continue
 c=round(x/(1.5*r));t=round(y/dy-(c%2)*.5);x=c*1.5*r;y=(t+(c%2)*.5)*dy
 pts=[(x+r*math.cos(i*math.pi/3),y+r*math.sin(i*math.pi/3)) for i in range(6)];poly=Polygon(pts)
 area=abs(geod.polygon_area_perimeter(*zip(*(lonlat(a,b) for a,b in pts)))[0])/1e6
 w=sum(length(poly.intersection(lines[i])) for i in tree.query(poly,predicate='intersects'))
 rows.append([c,t,round(area,1),round(w,2)])
D={'radius':r,'coverage':'34–60°E, 12–34°N; land-center cells only','reference':'Inherited GSHHG regional watercourse vectors and land mask; WGS84 geodesic measurements; modern reference, not historical reconstruction. Full hex area including any coastal water.','rows':rows}
(P/'data/cell_metrics.json').write_text(json.dumps(D,ensure_ascii=False,separators=(',',':')))
print('cells',len(rows),'with lines',sum(a[3]>0 for a in rows),'km',round(sum(a[3] for a in rows),1))
