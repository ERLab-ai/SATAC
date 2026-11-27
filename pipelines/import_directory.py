"""Stage the exact historical gazetteer and modern regional settlement sample."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import psycopg
from pipelines.import_genesis_places import uid

ROOT=Path(__file__).resolve().parents[1]/"data/migration_samples"
INPUTS={"historical":("gazetteer.v0.13.json","e824287cd8db93d93675745784254a52fd760f4f",190),
        "modern":("settlements.v0.13.json","7bf8ef310e1af9b8b908d8ab8cb9183e8d3bf77e",323)}

def load(collection):
    filename,blob,count=INPUTS[collection]
    raw=(ROOT/filename).read_bytes()
    if hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()!=blob:
        raise ValueError("legacy blob mismatch")
    d=json.loads(raw)
    records=d if collection=="historical" else d["records"]
    if len(records)!=count or len({r["id"] for r in records})!=count:
        raise ValueError("legacy inventory mismatch")
    return raw,d,records

def stage(conn):
    versions=[]
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(716035)")
        for collection,(_,blob,_) in INPUTS.items():
            raw,d,records=load(collection)
            source=uid("directory-source:"+blob)
            checksum=hashlib.sha256(raw).hexdigest()
            title="SATAC v0.13 — "+("gazetteer.json" if collection=="historical" else "settlements.json")
            conn.execute("INSERT INTO knowledge.source_version(id,title,content_sha256) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",(source,title,checksum))
            if conn.execute("SELECT content_sha256 FROM knowledge.source_version WHERE id=%s",(source,)).fetchone()[0]!=checksum:
                raise ValueError("source checksum mismatch")
            for r in records:
                key=str(r["id"])
                token=collection+":"+key
                eid,cid,vid=uid("directory-place:"+token),uid("directory-claim:"+token),uid("directory-version:"+blob+":"+token)
                payload={"collection":collection,"region_label":r["region"] if collection=="historical" else d["regions"][r["region"]],"record":r}
                content=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":"))
                conn.execute("INSERT INTO knowledge.entity VALUES(%s,'Place') ON CONFLICT DO NOTHING",(eid,))
                conn.execute("INSERT INTO knowledge.legacy_crosswalk VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",("directory-"+collection,key,eid))
                conn.execute("INSERT INTO knowledge.claim VALUES(%s) ON CONFLICT DO NOTHING",(cid,))
                conn.execute("""INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language,verification_status)
                    VALUES(%s,%s,%s,'DIRECTORY_ENTRY',%s,'ar','review_required') ON CONFLICT(id) DO NOTHING""",(vid,cid,eid,content))
                if conn.execute("SELECT claim_id,subject_id,object_text FROM knowledge.claim_version WHERE id=%s",(vid,)).fetchone()!=(cid,eid,content):
                    raise ValueError("directory version mismatch")
                conn.execute("INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator,stance) VALUES(%s,%s,%s,%s,'context') ON CONFLICT DO NOTHING",
                    (uid("directory-evidence:"+str(vid)),vid,source,("records/" if collection=="modern" else "id/")+key))
                versions.append(vid)
    return versions

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage",required=True,action="store_true")
    p.parse_args()
    with psycopg.connect(os.environ["SATAC_IMPORT_DSN"]) as conn:
        print(json.dumps({"staged_versions":[str(v) for v in stage(conn)]}))
