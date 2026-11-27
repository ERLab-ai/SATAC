"""Stage original route segments; preserve source distances and geometry."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import psycopg
from pipelines.import_genesis_places import uid

ROOT=Path(__file__).resolve().parents[1]/"data/migration_samples"
BLOB="8774e4dc6e2d9bd44c676de285025b5f678214a3"
NAMES_BLOB="01494b840a0e81cd0568c5184d14c23b62e5e8d3"

def verified(name,blob):
    raw=(ROOT/name).read_bytes()
    if hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()!=blob:
        raise ValueError("legacy blob mismatch")
    return raw,json.loads(raw)

def load():
    raw,edges=verified("routes.v0.13.json",BLOB)
    if len(edges)!=145 or len({e["id"] for e in edges})!=145 or len({e[k] for e in edges for k in ("from_id","to_id")})!=135:
        raise ValueError("route inventory mismatch")
    verified("route_names.v0.13.json",NAMES_BLOB)
    return raw,edges

def stage(conn):
    raw,edges=load()
    source=uid("routes-source:"+BLOB)
    checksum=hashlib.sha256(raw).hexdigest()
    versions=[]
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(716036)")
        conn.execute("INSERT INTO knowledge.source_version(id,title,content_sha256) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",(source,"SATAC v0.13 — routes.json",checksum))
        if conn.execute("SELECT content_sha256 FROM knowledge.source_version WHERE id=%s",(source,)).fetchone()[0]!=checksum:
            raise ValueError("source checksum mismatch")
        for e in edges:
            key=e["id"]
            eid,cid,vid=uid("route:"+key),uid("route-claim:"+key),uid("route-version:"+BLOB+":"+key)
            content=json.dumps(e,ensure_ascii=False,sort_keys=True,separators=(",",":"))
            conn.execute("INSERT INTO knowledge.entity VALUES(%s,'Route') ON CONFLICT DO NOTHING",(eid,))
            conn.execute("INSERT INTO knowledge.legacy_crosswalk VALUES('routes-v0.13',%s,%s) ON CONFLICT DO NOTHING",(key,eid))
            conn.execute("INSERT INTO knowledge.claim VALUES(%s) ON CONFLICT DO NOTHING",(cid,))
            conn.execute("""INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language,verification_status)
                VALUES(%s,%s,%s,'ROUTE_SEGMENT',%s,'ar','review_required') ON CONFLICT(id) DO NOTHING""",(vid,cid,eid,content))
            if conn.execute("SELECT claim_id,subject_id,object_text FROM knowledge.claim_version WHERE id=%s",(vid,)).fetchone()!=(cid,eid,content):
                raise ValueError("route version mismatch")
            conn.execute("INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator,stance) VALUES(%s,%s,%s,%s,'context') ON CONFLICT DO NOTHING",(uid("route-evidence:"+str(vid)),vid,source,"id/"+key))
            versions.append(vid)
    return versions

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage",required=True,action="store_true")
    p.parse_args()
    with psycopg.connect(os.environ["SATAC_IMPORT_DSN"]) as conn:
        print(json.dumps({"staged_versions":[str(v) for v in stage(conn)]}))
