"""Convert the original equirectangular SVG paths without inventing geography."""
import json
import re
from hashlib import sha256
from shapely.geometry import LineString, box, mapping

WORLD_HASH="4c8e268ba75045b73be09b4f2bcabffd955479493b5a6a7bbee4fc21b212b0ed"
PAIR=re.compile(r"[ML](-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")

def coords(path):
    if PAIR.sub("",path).replace("Z","").strip():
        raise ValueError("unexpected path grammar")
    result=[]
    for x,y in PAIR.findall(path):
        p=[round(float(x)*360/1000-180,7),round(90-float(y)*180/500,7)]
        if not (-180<=p[0]<=180 and -90<=p[1]<=90):
            raise ValueError("coordinate outside WGS84")
        result.append(p)
    return result

def feature(kind,c,props):
    return {"type":"Feature","geometry":{"type":kind,"coordinates":c},"properties":props}

def write(path,features):
    path.write_text(json.dumps({"type":"FeatureCollection","features":features},separators=(",",":")),encoding="utf-8")
    return sha256(path.read_bytes()).hexdigest()

def build_vectors(geo,world_path,out):
    raw=world_path.read_bytes()
    if sha256(raw).hexdigest()!=WORLD_HASH:
        raise ValueError("legacy worldtiles SHA-256 differs")
    world=json.loads(raw)
    cells=[]
    for color,group in world["paths"]:
        if not re.fullmatch(r"#[0-9a-f]{6}",color):
            raise ValueError("invalid color")
        for path in group.split("Z"):
            if not path: continue
            ring=coords(path)
            if len(ring)!=6 or len(set(map(tuple,ring)))!=6:
                raise ValueError("invalid hexagon")
            ring.append(ring[0])
            # Original clockwise SVG screen coordinates become clockwise geographic rings;
            # normalize exterior rings to counterclockwise.
            area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]))
            if area<0: ring.reverse()
            cells.append(feature("Polygon",[ring],{"color":color}))
    if len(cells)!=world["count"] or len(cells)!=37209 or len(world["land"])!=23952:
        raise ValueError("legacy cell count mismatch")
    hashes={"hex.geojson":write(out/"hex.geojson",cells)}
    counts={}
    for key in ("worldRivers","regionalRivers"):
        lines=[]
        for path in geo[key]:
            line=coords(path)
            if len(set(map(tuple,line)))<2:
                raise ValueError("degenerate river")
            lines.append(feature("LineString",line,{}))
        counts[key]=len(lines)
        hashes[key+".geojson"]=write(out/(key+".geojson"),lines)
    if counts!={"worldRivers":9325,"regionalRivers":1848}:
        raise ValueError("river count mismatch")
    # Preserve global rivers at higher zoom outside the regional source envelope.
    # Clip coarse reference geometry instead of double-drawing coarse and fine lines.
    envelope=box(18,0,75,45)
    outside=[]
    def lineparts(g):
        if g.geom_type=="LineString" and not g.is_empty and g.length>0:
            yield g
        elif hasattr(g,"geoms"):
            for part in g.geoms:
                yield from lineparts(part)
    for path in geo["worldRivers"]:
        for line in lineparts(LineString(coords(path)).difference(envelope)):
            outside.append(feature("LineString",mapping(line)["coordinates"],{}))
    hashes["outsideRivers.geojson"]=write(out/"outsideRivers.geojson",outside)
    print("High-zoom coarse river pieces outside regional coverage:",len(outside))
    print("Verified worldtiles SHA-256; converted",len(cells),"hexagons and river paths",counts)
    return hashes,{"worldtiles_sha256":WORLD_HASH,"hex_cells":len(cells),"land_centers":len(world["land"]),"river_paths":counts,"legacy_bbox":world["bbox"]}
