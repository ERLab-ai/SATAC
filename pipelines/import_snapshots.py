"""Import source snapshots, not historical validity intervals. Never execute archived JS."""
import argparse
import hashlib
import json
import os
import re
import psycopg
from pipelines.import_genesis_places import uid
from pipelines.import_routes import verified

POLYGON_BLOB="126ff04d1a1e8c83b306252ace01fe32a567272d"
JS_BLOB="d567e3ab843ae329a364d00cb0a8f988db4504bd"
from pipelines.import_routes import ROOT

def load():
    raw,territories=verified("territories.v0.13.json",POLYGON_BLOB)
    js=(ROOT/"territories.v0.13.js").read_bytes()
    if hashlib.sha1(b"blob "+str(len(js)).encode()+b"\0"+js).hexdigest()!=JS_BLOB:
        raise ValueError("legacy script blob mismatch")
    literal=js.decode().split("const milestones=",1)[1].split(";\n",1)[0]
    pattern=r"(\d+):\{title:'([^']*)',place:'([^']*)',p:(\[[^\]]+\]),article:'([^']*)',text:'([^']*)'\}"
    milestones=[{"type":"milestone","year":int(y),"record":{"title":title,"place":place,"p":json.loads(p),"article":article,"text":text}} for y,title,place,p,article,text in re.findall(pattern,literal)]
    records=[{"type":"territory","year":t["year"],"record":t} for t in territories]
    if len(records)!=27 or {x["year"] for x in records}!={-200,600,800,1000,1279} or len({t["id"] for t in territories})!=27 or [x["year"] for x in milestones]!=[1727,1824,1902,1932]:
        raise ValueError("snapshot inventory mismatch")
    return raw,js,records+milestones

def stage(conn):
    raw,js,records=load()
    versions=[]
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(716037)")
        for blob,content,title in ((POLYGON_BLOB,raw,"SATAC v0.13 — territories.json"),(JS_BLOB,js,"SATAC v0.13 — territories.js")):
            source=uid("snapshot-source:"+blob)
            checksum=hashlib.sha256(content).hexdigest()
            conn.execute("INSERT INTO knowledge.source_version(id,title,content_sha256) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",(source,title,checksum))
            if conn.execute("SELECT content_sha256 FROM knowledge.source_version WHERE id=%s",(source,)).fetchone()[0]!=checksum:
                raise ValueError("snapshot source mismatch")
        for item in records:
            y=item["year"]
            polygon=item["type"]=="territory"
            blob=POLYGON_BLOB if polygon else JS_BLOB
            key=item["record"]["id"] if polygon else "milestone:"+str(y)
            eid,cid,vid=uid("snapshot-work:"+key),uid("snapshot-claim:"+key),uid("snapshot-version:"+blob+":"+key)
            content=json.dumps(item,ensure_ascii=False,sort_keys=True,separators=(",",":"))
            conn.execute("INSERT INTO knowledge.entity VALUES(%s,'Work') ON CONFLICT DO NOTHING",(eid,))
            conn.execute("INSERT INTO knowledge.legacy_crosswalk VALUES('snapshots-v0.13',%s,%s) ON CONFLICT DO NOTHING",(key,eid))
            conn.execute("INSERT INTO knowledge.claim VALUES(%s) ON CONFLICT DO NOTHING",(cid,))
            conn.execute("""INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language,verification_status)
                VALUES(%s,%s,%s,'HISTORICAL_SNAPSHOT',%s,'ar','review_required') ON CONFLICT(id) DO NOTHING""",(vid,cid,eid,content))
            if conn.execute("SELECT claim_id,subject_id,object_text FROM knowledge.claim_version WHERE id=%s",(vid,)).fetchone()!=(cid,eid,content):
                raise ValueError("snapshot version mismatch")
            a=y+1 if y<0 else y
            conn.execute("""INSERT INTO knowledge.temporal_extent(version_id,start_kind,start_low,start_high,end_kind,end_low,end_high,original_text,calendar,precision_label,normalization_method)
                VALUES(%s,'bounded',%s,%s,'bounded',%s,%s,%s,'historical BCE/CE','source snapshot year','historical BCE maps to astronomical 1-BCE') ON CONFLICT DO NOTHING""",(vid,a,a,a,a,str(abs(y))+(" BCE" if y<0 else " CE")))
            conn.execute("INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator,stance) VALUES(%s,%s,%s,%s,'context') ON CONFLICT DO NOTHING",(uid("snapshot-evidence:"+str(vid)),vid,uid("snapshot-source:"+blob),key))
            versions.append(vid)
    return versions

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage",required=True,action="store_true")
    p.parse_args()
    with psycopg.connect(os.environ["SATAC_IMPORT_DSN"]) as conn:
        print(json.dumps({"staged_versions":[str(v) for v in stage(conn)]}))
