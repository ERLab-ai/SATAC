"""Stage exact legacy geology records, not geological validity intervals."""
import argparse
import hashlib
import json
import os
import psycopg
from pipelines.import_routes import verified,ROOT
from pipelines.import_genesis_places import uid

BLOB="3bc57d1e91333e81952f95df329ddef246658aeb"
SOURCES=(("provinces_source.v0.13.psv","22a408c953150c1d34781e9f6ef0182d7cd268c0"),("volcanic_sites.v0.13.psv","29c694f802c71935c338585e6a993da247c47f3c"))

def load():
    raw,d=verified("geology.v0.13.json",BLOB)
    for name,blob in SOURCES:
        data=(ROOT/name).read_bytes()
        if hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()!=blob:
            raise ValueError("source table mismatch")
    p,v=d["provinces"],d["volcanoes"]
    if len(p)!=44 or len(v)!=12 or len({x["id"] for x in p})!=44 or len({x["id"] for x in v})!=12 or d["excluded"]!=[29] or len(d["cell_provinces"])!=1847:
        raise ValueError("geology inventory mismatch")
    if not all(set(ids)<={x["id"] for x in p} for ids in d["cell_provinces"].values()):
        raise ValueError("invalid cell reference")
    return raw,d

def stage(conn):
    raw,d=load()
    source=uid("geology-source:"+BLOB)
    checksum=hashlib.sha256(raw).hexdigest()
    versions=[]
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(716038)")
        conn.execute("INSERT INTO knowledge.source_version(id,title,content_sha256) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",(source,"SATAC v0.13 — geology.json",checksum))
        if conn.execute("SELECT content_sha256 FROM knowledge.source_version WHERE id=%s",(source,)).fetchone()[0]!=checksum:
            raise ValueError("source mismatch")
        for kind,rows in (("province",d["provinces"]),("volcano",d["volcanoes"])):
            for r in rows:
                token=kind+":"+str(r["id"])
                eid,cid,vid=uid("geology-place:"+token),uid("geology-claim:"+token),uid("geology-version:"+BLOB+":"+token)
                item={"type":kind,"record":r}
                if kind=="province":
                    item.update(reference=d["reference"],simplification_deg=d["simplification_deg"])
                content=json.dumps(item,ensure_ascii=False,sort_keys=True,separators=(",",":"))
                conn.execute("INSERT INTO knowledge.entity VALUES(%s,'Place') ON CONFLICT DO NOTHING",(eid,))
                conn.execute("INSERT INTO knowledge.legacy_crosswalk VALUES('geology-v0.13',%s,%s) ON CONFLICT DO NOTHING",(token,eid))
                conn.execute("INSERT INTO knowledge.claim VALUES(%s) ON CONFLICT DO NOTHING",(cid,))
                conn.execute("""INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language,verification_status)
                    VALUES(%s,%s,%s,'GEOLOGY_RECORD',%s,'ar','review_required') ON CONFLICT(id) DO NOTHING""",(vid,cid,eid,content))
                if conn.execute("SELECT claim_id,subject_id,object_text FROM knowledge.claim_version WHERE id=%s",(vid,)).fetchone()!=(cid,eid,content):
                    raise ValueError("geology version mismatch")
                conn.execute("INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator,stance) VALUES(%s,%s,%s,%s,'context') ON CONFLICT DO NOTHING",(uid("geology-evidence:"+str(vid)),vid,source,token))
                versions.append(vid)
    return versions

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage",required=True,action="store_true")
    p.parse_args()
    with psycopg.connect(os.environ["SATAC_IMPORT_DSN"]) as conn:
        print(json.dumps({"staged_versions":[str(v) for v in stage(conn)]}))
