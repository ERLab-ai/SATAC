"""Stage original measured cell metrics and pinned geology associations."""
import argparse
import hashlib
import json
import os
import psycopg
from pipelines.import_routes import verified
from pipelines.import_geology import load as load_geology,BLOB as GEO_BLOB
from pipelines.import_genesis_places import uid
BLOB="f972ecd97ea4173c8fd242c6cb7fd34d7055b992"

def load():
    raw,d=verified("cell_metrics.v0.13.json",BLOB)
    geo_raw,g=load_geology()
    keys={f"{r[0]},{r[1]}" for r in d["rows"]}
    if len(d["rows"])!=2480 or len(keys)!=2480 or not set(g["cell_provinces"])<=keys or d["radius"]!=0.72:
        raise ValueError("grid inventory mismatch")
    return raw,d,geo_raw,g

def stage(conn):
    raw,d,geo_raw,g=load()
    source=uid("cell-source:"+BLOB)
    geo_source=uid("geology-source:"+GEO_BLOB)
    versions=[]
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(716039)")
        checksum=hashlib.sha256(raw).hexdigest()
        conn.execute("INSERT INTO knowledge.source_version(id,title,content_sha256) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",(source,"SATAC v0.13 — cell_metrics.json",checksum))
        if conn.execute("SELECT content_sha256 FROM knowledge.source_version WHERE id=%s",(source,)).fetchone()[0]!=checksum:
            raise ValueError("source mismatch")
        if conn.execute("SELECT content_sha256 FROM knowledge.source_version WHERE id=%s",(geo_source,)).fetchone()!=(hashlib.sha256(geo_raw).hexdigest(),):
            raise ValueError("stage geology first")
        for c,t,area,water in d["rows"]:
            key=f"{c},{t}"
            eid,cid,vid=uid("cell-place:"+key),uid("cell-claim:"+key),uid("cell-version:"+BLOB+":"+GEO_BLOB+":"+key)
            item={"id":key,"c":c,"t":t,"area_km2":area,"water_km":water,"radius":d["radius"],"province_ids":g["cell_provinces"].get(key,[])}
            content=json.dumps(item,sort_keys=True,separators=(",",":"))
            conn.execute("INSERT INTO knowledge.entity VALUES(%s,'Place') ON CONFLICT DO NOTHING",(eid,))
            conn.execute("INSERT INTO knowledge.legacy_crosswalk VALUES('cells-v0.13',%s,%s) ON CONFLICT DO NOTHING",(key,eid))
            conn.execute("INSERT INTO knowledge.claim VALUES(%s) ON CONFLICT DO NOTHING",(cid,))
            conn.execute("""INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language,verification_status)
              VALUES(%s,%s,%s,'CELL_METRIC',%s,'ar','review_required') ON CONFLICT(id) DO NOTHING""",(vid,cid,eid,content))
            if conn.execute("SELECT claim_id,subject_id,object_text FROM knowledge.claim_version WHERE id=%s",(vid,)).fetchone()!=(cid,eid,content):
                raise ValueError("cell version mismatch")
            for tag,sid,locator in (("metrics",source,"rows/"+key),("geology",geo_source,"cell_provinces/"+key)):
                conn.execute("INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator,stance) VALUES(%s,%s,%s,%s,'context') ON CONFLICT DO NOTHING",(uid("cell-evidence:"+str(vid)+":"+tag),vid,sid,locator))
            versions.append(vid)
    return versions

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage",required=True,action="store_true")
    p.parse_args()
    with psycopg.connect(os.environ["SATAC_IMPORT_DSN"]) as conn:
        print(json.dumps({"staged_versions":[str(v) for v in stage(conn)]}))
