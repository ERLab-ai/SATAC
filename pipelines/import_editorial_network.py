"""Stage original curated connections and journeys; never infer historical routes."""
import argparse
import json
import os
import psycopg
from pipelines.import_genesis_places import uid
from pipelines.import_encyclopedia import load,BLOB

def stage(conn):
    _,d=load()
    ids={a["id"] for a in d["articles"]}
    if len(d["links"])!=13 or len(d["journeys"])!=8:
        raise ValueError("network inventory mismatch")
    source=uid("encyclopedia-source:"+BLOB)
    versions=[]
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(716034)")
        for key,predicate in (("links","EDITORIAL_LINK"),("journeys","EDITORIAL_JOURNEY")):
            for ordinal,record in enumerate(d[key]):
                endpoints=record[:2] if key=="links" else record["ids"]
                if not set(endpoints)<=ids:
                    raise ValueError("unknown article endpoint")
                for endpoint in endpoints:
                    if not conn.execute("SELECT 1 FROM knowledge.legacy_crosswalk WHERE namespace='encyclopedia-v0.13' AND legacy_id=%s",(endpoint,)).fetchone():
                        raise ValueError("stage encyclopedia first")
                token=key+":"+str(ordinal)
                eid,cid,vid=uid("editorial-work:"+token),uid("editorial-claim:"+token),uid("editorial-version:"+BLOB+":"+token)
                content=json.dumps({"ordinal":ordinal,"record":record},ensure_ascii=False,sort_keys=True,separators=(",",":"))
                conn.execute("INSERT INTO knowledge.entity VALUES(%s,'Work') ON CONFLICT DO NOTHING",(eid,))
                conn.execute("INSERT INTO knowledge.claim VALUES(%s) ON CONFLICT DO NOTHING",(cid,))
                conn.execute("""INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language,verification_status)
                    VALUES(%s,%s,%s,%s,%s,'ar','review_required') ON CONFLICT(id) DO NOTHING""",(vid,cid,eid,predicate,content))
                if conn.execute("SELECT claim_id,subject_id,predicate,object_text FROM knowledge.claim_version WHERE id=%s",(vid,)).fetchone()!=(cid,eid,predicate,content):
                    raise ValueError("editorial version mismatch")
                conn.execute("INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator,stance) VALUES(%s,%s,%s,%s,'context') ON CONFLICT DO NOTHING",
                    (uid("editorial-evidence:"+str(vid)),vid,source,token.replace(":","/")))
                versions.append(vid)
    return versions

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage",required=True,action="store_true")
    p.parse_args()
    with psycopg.connect(os.environ["SATAC_IMPORT_DSN"]) as conn:
        print(json.dumps({"staged_versions":[str(v) for v in stage(conn)]}))
