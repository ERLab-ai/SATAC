"""Build regional display excerpts from manually transferred upstream simplified coordinates.
Each row is an extract of a source feature, not a reconstruction from prose.
Raw TSV coordinates are tenths of a degree; components deliberately selected for region.
"""
from pathlib import Path
import json
from shapely.geometry import Polygon, MultiPolygon, mapping, box
from shapely import make_valid
P=Path(__file__).resolve().parent
sha={-200:'48afd719a925491e2fddd446705959e5edeaf080',600:'a677b61865c3888b6c136eb2c96f5a3fe0738695',800:'3bc0394a066bae9b39e0c8ca0dc5ec15d422d179',1000:'c0cd99f28d0b490a7147c391f2d2ac72c0434015',1279:'a2d1bcc0ca4c487adf1cfdf34bfb5ccac10509a4'}
features=[]
def polygon_parts(g):
    if g.geom_type=='Polygon': return [g] if not g.is_empty else []
    if hasattr(g,'geoms'): return [p for a in g.geoms for p in polygon_parts(a)]
    return []
for i,line in enumerate((P/'data/territories_sample.tsv').read_text().splitlines()):
    yr,orig,name,subject,kind,encoded=line.split('|');year=int(yr)
    polygons=[]
    for part in encoded.split(';'):
        rings=[]
        for ring in part.split('/'):
            nums=list(map(int,ring.split(',')))
            rings.append([(x/10,y/10) for x,y in zip(nums[::2],nums[1::2])])
        polygons.extend(polygon_parts(make_valid(Polygon(rings[0],rings[1:]))))
    if not polygons: raise ValueError(orig)
    from shapely.ops import unary_union
    geom=unary_union(polygons)
    assert geom.is_valid
    # Representative anchor in the regional viewport, not a historical capital.
    local=geom.intersection(box(25,10,62,42));anchor=(local if not local.is_empty else geom).representative_point()
    filename='world_bc200.geojson' if year==-200 else f'world_{year}.geojson'
    features.append(dict(id=f't{i+1:02}',year=year,name=name,source_name=orig,subject=subject,kind=kind,border_precision=1,geometry=mapping(geom),label=[round(anchor.x,2),round(anchor.y,2)],source_url=f'https://github.com/aourednik/historical-basemaps/blob/{sha[year]}/geojson/{filename}',source_blob_sha=sha[year]))
    # The source link uses a Git blob SHA, not a commit SHA. Point to the actual blob endpoint.
    features[-1]['source_url']=f'https://api.github.com/repos/aourednik/historical-basemaps/git/blobs/{sha[year]}'
    features[-1]['browse_url']=f'https://github.com/aourednik/historical-basemaps/blob/{"a86650160b30761fdf7cff449129a3aac8dd00b8" if year==-200 else "master"}/geojson/{filename}'
(P/'data/territories.json').write_text(json.dumps(features,ensure_ascii=False,separators=(',',':')))
print('Features:',len(features),'snapshots:',sorted(set(x['year'] for x in features)))
