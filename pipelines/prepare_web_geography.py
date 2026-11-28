"""Rebuild exact legacy geography; reproject reference imagery into Web Mercator XYZ.
No elevation samples, historical terrain model, or invented labels.
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from legacy_geography.vector_assets import build_vectors

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
EXPECTED="7df821b015257fff29ec70c7971c11bca41aa3d32916e4190db6ec732f5d8529"
MAX_Z=2

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def build(source,world,out):
    if digest(source)!=EXPECTED:
        raise ValueError("legacy geography SHA-256 differs")
    data=json.loads(source.read_bytes())
    out.mkdir(parents=True,exist_ok=True)
    labels=data["labels"]
    if len(labels)!=91:
        raise ValueError("unexpected label count")
    (out/"labels.json").write_text(json.dumps(labels,ensure_ascii=False),encoding="utf-8")
    hashes={}
    for key in ("relief","etopo"):
        original=Image.open(io.BytesIO(base64.b64decode(data[key].split(",",1)[1]))).convert("RGB")
        # Source is global equirectangular; longitude remains linear. Interpolate
        # latitude at Web Mercator pixel centers. Clip to +/-85.05112878 degrees.
        size=512*(2**MAX_Z)
        resized=original.resize((size,original.height),Image.Resampling.LANCZOS)
        pixels=np.asarray(resized,dtype=np.float32)
        ys=(np.arange(size)+0.5)/size
        lat=np.degrees(np.arctan(np.sinh(np.pi*(1-2*ys))))
        rows=np.clip((90-lat)/180*original.height-0.5,0,original.height-1)
        low=np.floor(rows).astype(int)
        hi=np.minimum(low+1,original.height-1)
        w=(rows-low)[:,None,None]
        projected=Image.fromarray(np.rint(pixels[low]*(1-w)+pixels[hi]*w).astype(np.uint8))
        for z in range(MAX_Z+1):
            n=2**z
            image=projected.resize((512*n,512*n),Image.Resampling.LANCZOS)
            for x in range(n):
                for y in range(n):
                    p=out/key/str(z)/str(x)/(str(y)+".webp")
                    p.parent.mkdir(parents=True,exist_ok=True)
                    image.crop((x*512,y*512,(x+1)*512,(y+1)*512)).save(p,"WEBP",quality=85,method=4)
                    hashes[str(p.relative_to(out))]=digest(p)
    hashes["labels.json"]=digest(out/"labels.json")
    vectors,meta=build_vectors(data,world,out)
    raster_count=sum(k.endswith(".webp") for k in hashes)
    hashes.update(vectors)
    (out/"manifest.json").write_text(json.dumps({"legacy_sha256":EXPECTED,"labels":91,"maxzoom":MAX_Z,"files":hashes,**meta},indent=2)+"\n")
    print("Verified source SHA-256; generated",raster_count,"global raster tiles,",len(hashes)-raster_count,"other assets and",len(labels),"labels")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--legacy-geography",type=Path)
    p.add_argument("--legacy-worldtiles",type=Path)
    p.add_argument("--output",type=Path,default=ROOT/"apps/web/public/physical")
    args=p.parse_args()
    if bool(args.legacy_geography)!=bool(args.legacy_worldtiles):
        p.error('supply both original files or neither')
    if args.legacy_geography:
        build(args.legacy_geography,args.legacy_worldtiles,args.output)
    else:
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d)
            (tmp/"data").mkdir()
            shutil.copyfile(ROOT/"pipelines/legacy_geography/prepare_geography.py",tmp/"prepare_geography.py")
            subprocess.run([sys.executable,str(tmp/"prepare_geography.py")],check=True)
            shutil.copyfile(ROOT/"pipelines/legacy_geography/prepare_world.py",tmp/"prepare_world.py")
            subprocess.run([sys.executable,str(tmp/"prepare_world.py")],check=True)
            build(tmp/"data/geography.json",tmp/"data/worldtiles.json",args.output)

if __name__=="__main__":
    main()
