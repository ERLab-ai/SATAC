"""Stage the complete, byte-identical v0.13 main encyclopedia (not atomic fact extraction)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import psycopg
from pipelines.import_genesis_places import uid

SOURCE=Path(__file__).resolve().parents[1]/"data/migration_samples/encyclopedia.v0.13.json"
BLOB="0f7f8a35bc75a2603f22217117a63c78cb776801"

def load():
    raw=SOURCE.read_bytes()
    if hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()!=BLOB:
        raise ValueError("legacy Git blob differs")
    d=json.loads(raw)
    ids={a["id"] for a in d["articles"]}
    if len(ids)!=len(d["articles"]) or len(ids)!=50 or len(d["sources"])!=24:
        raise ValueError("legacy inventory mismatch")
    if any(not set(a["related"])<=ids or not set(a["sources"])<=d["sources"].keys() for a in d["articles"]):
        raise ValueError("broken legacy references")
    return raw,d

def stage(conn):
    raw,d=load()
    source=uid("encyclopedia-source:"+BLOB)
    checksum=hashlib.sha256(raw).hexdigest()
    versions=[]
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(716034)")
        conn.execute("INSERT INTO knowledge.source_version(id,title,content_sha256) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",(source,"SATAC v0.13 — encyclopedia.json",checksum))
        if conn.execute("SELECT content_sha256 FROM knowledge.source_version WHERE id=%s",(source,)).fetchone()[0]!=checksum:
            raise ValueError("source checksum mismatch")
        for a in d["articles"]:
            key=a["id"]
            eid,cid,vid=uid("article-work:"+key),uid("article-claim:"+key),uid("article-version:"+BLOB+":"+key)
            payload={**a,"bibliography":[{"id":s,"title":d["sources"][s][0],"url":d["sources"][s][1]} for s in a["sources"]]}
            content=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":"))
            conn.execute("INSERT INTO knowledge.entity VALUES(%s,'Work') ON CONFLICT DO NOTHING",(eid,))
            conn.execute("INSERT INTO knowledge.legacy_crosswalk VALUES('encyclopedia-v0.13',%s,%s) ON CONFLICT DO NOTHING",(key,eid))
            conn.execute("INSERT INTO knowledge.claim VALUES(%s) ON CONFLICT DO NOTHING",(cid,))
            conn.execute("""INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language,verification_status)
              VALUES(%s,%s,%s,'ARTICLE',%s,'ar','review_required') ON CONFLICT(id) DO NOTHING""",(vid,cid,eid,content))
            if conn.execute("SELECT claim_id,subject_id,object_text FROM knowledge.claim_version WHERE id=%s",(vid,)).fetchone()!=(cid,eid,content):
                raise ValueError("article version mismatch")
            conn.execute("INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator,stance) VALUES(%s,%s,%s,%s,'context') ON CONFLICT DO NOTHING",(uid("article-evidence:"+str(vid)),vid,source,"articles/"+key))
            versions.append(vid)
    return versions

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage",action="store_true",required=True)
    p.parse_args()
    with psycopg.connect(os.environ["SATAC_IMPORT_DSN"]) as conn:
        ids=stage(conn)
    print(json.dumps({"staged_versions":[str(i) for i in ids]}))

if __name__=="__main__":
    main()
