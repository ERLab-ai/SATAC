"""Stage byte-identical legacy historical stories and geological heritage topics."""
import argparse
import hashlib
import json
import os
import psycopg
from pipelines.import_routes import verified
from pipelines.import_genesis_places import uid

STORIES="dae0e2a27f36c4fc53b0caba3a862ec43cf4ee8b"
GEOSITES="93f52ca26c91eb5399a05ee20598d972b9a7558e"

def load():
    a,stories=verified("gazetteer_stories.v0.13.json",STORIES)
    b,sites=verified("geosites.v0.13.json",GEOSITES)
    if len(stories)!=5 or len(sites)!=2 or len({x["id"] for x in sites})!=2:
        raise ValueError("topic inventory mismatch")
    return [(STORIES,a,"gazetteer_stories.json",[{"type":"story","id":k,"record":v} for k,v in stories.items()]),
            (GEOSITES,b,"geosites.json",[{"type":"geosite","id":x["id"],"record":x} for x in sites])]

def stage(conn):
    versions=[]
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(716040)")
        for blob,raw,filename,items in load():
            source=uid("topic-source:"+blob)
            checksum=hashlib.sha256(raw).hexdigest()
            conn.execute("INSERT INTO knowledge.source_version(id,title,content_sha256) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",(source,"SATAC v0.13 — "+filename,checksum))
            if conn.execute("SELECT content_sha256 FROM knowledge.source_version WHERE id=%s",(source,)).fetchone()!=(checksum,):
                raise ValueError("topic source mismatch")
            for item in items:
                key=item["type"]+":"+item["id"]
                if item["type"]=="story" and not conn.execute("SELECT 1 FROM knowledge.legacy_crosswalk WHERE namespace='directory-historical' AND legacy_id=%s",(item["id"],)).fetchone():
                    raise ValueError("stage directory first")
                eid,cid,vid=uid("topic-work:"+key),uid("topic-claim:"+key),uid("topic-version:"+blob+":"+key)
                content=json.dumps(item,ensure_ascii=False,sort_keys=True,separators=(",",":"))
                conn.execute("INSERT INTO knowledge.entity VALUES(%s,'Work') ON CONFLICT DO NOTHING",(eid,))
                conn.execute("INSERT INTO knowledge.legacy_crosswalk VALUES('extended-topics-v0.13',%s,%s) ON CONFLICT DO NOTHING",(key,eid))
                conn.execute("INSERT INTO knowledge.claim VALUES(%s) ON CONFLICT DO NOTHING",(cid,))
                conn.execute("""INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language,verification_status)
                  VALUES(%s,%s,%s,'EXTENDED_TOPIC',%s,'ar','review_required') ON CONFLICT(id) DO NOTHING""",(vid,cid,eid,content))
                if conn.execute("SELECT claim_id,subject_id,object_text FROM knowledge.claim_version WHERE id=%s",(vid,)).fetchone()!=(cid,eid,content):
                    raise ValueError("topic version mismatch")
                conn.execute("INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator,stance) VALUES(%s,%s,%s,%s,'context') ON CONFLICT DO NOTHING",(uid("topic-evidence:"+str(vid)),vid,source,item["id"]))
                versions.append(vid)
    return versions

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage",required=True,action="store_true")
    p.parse_args()
    with psycopg.connect(os.environ["SATAC_IMPORT_DSN"]) as conn:
        print(json.dumps({"staged_versions":[str(v) for v in stage(conn)]}))
