"""Fail CI on unclassified files in the web distribution.

This gate classifies file paths and checks tracked static source bytes. It is not
a scanner for factual content inside generated JavaScript or a licensing audit.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ({f"category-{i}.svg" for i in range(13)}
       | {f"{name}.svg" for name in ("tomb","rock","oasis","port","route","fort","globe","dam","terrace","dune","industry")}
       | {f"gaz-{name}.svg" for name in ("metropoles","capitals","towns","waystations","villages","regions","sites","waters")})

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inventory(root, public):
    entries=list(root.rglob("*"))
    if any(p.is_symlink() or not (p.is_file() or p.is_dir()) for p in entries):
        raise ValueError("non-regular distribution entry")
    actual={p.relative_to(root).as_posix() for p in entries if p.is_file()}
    manifest=json.loads((root/"physical/manifest.json").read_text(encoding="utf-8"))
    physical={f"physical/{name}" for name in manifest["files"]}|{"physical/manifest.json"}
    tracked={"land.geojson"}|{f"legacy-art/{name}" for name in ART}
    app=actual-(physical|tracked)
    expected={"index.html","assets/maplibre-gl-worker.mjs"}
    scripts={p for p in app if re.fullmatch(r"assets/index-[A-Za-z0-9_-]+[.]js",p)}
    styles={p for p in app if re.fullmatch(r"assets/index-[A-Za-z0-9_-]+[.]css",p)}
    if len(scripts)!=1 or len(styles)!=1 or app!=expected|scripts|styles or not physical|tracked<=actual:
        raise ValueError("unexpected or missing distribution file; classify before serving")
    for name in tracked:
        if digest(root/name)!=digest(public/name):
            raise ValueError("tracked static source mismatch: "+name)
    grouped={}
    for name in sorted(physical|tracked):
        grouped.setdefault(digest(root/name),[]).append(name)
    return {"format":"satac-distribution-inventory-v1",
            "protected_static":sorted(physical|tracked),"application":sorted(app),
            "identical_static_paths":[names for names in grouped.values() if len(names)>1]}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,default=ROOT/"apps/web/dist")
    p.add_argument("--public",type=Path,default=ROOT/"apps/web/public")
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    data=inventory(a.root,a.public)
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print("PASS: classified",len(data["protected_static"]),"protected static and",len(data["application"]),"application files; identical static paths recorded")
