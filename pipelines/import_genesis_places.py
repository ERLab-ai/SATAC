"""Deterministic stage-only import of pinned v0.13 records."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID, uuid5
import psycopg

SAMPLE = Path(__file__).resolve().parents[1] / "data/migration_samples/genesis_places.json"
NS = UUID("ec1142ca-283e-5ae9-a4df-df0d816f9244")


def uid(key):
    return uuid5(NS, key)


def import_sample(conn):
    raw=SAMPLE.read_bytes()
    d=json.loads(raw)
    source_id=uid("source:"+d["provenance"]["git_blob_sha"])
    sample_hash=hashlib.sha256(raw).hexdigest()
    versions=[]
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(716033)")
        conn.execute("INSERT INTO knowledge.source_version(id,title,content_sha256) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                     (source_id,"SATAC v0.13 — knowledge.json (selected records)",sample_hash))
        if conn.execute("SELECT content_sha256 FROM knowledge.source_version WHERE id=%s",(source_id,)).fetchone()[0]!=sample_hash:
            raise ValueError("changed sample; explicit migration required")
        for e in d["entities"]:
            if e["kind"]!="place":
                raise ValueError("sample supports place only")
            eid=uid("entity:"+e["id"])
            conn.execute("INSERT INTO knowledge.entity(id,kind) VALUES(%s,'Place') ON CONFLICT DO NOTHING",(eid,))
            conn.execute("INSERT INTO knowledge.legacy_crosswalk(namespace,legacy_id,entity_id) VALUES('genesis-0.1',%s,%s) ON CONFLICT DO NOTHING",(e["id"],eid))
            for lang,key in (("ar","name"),("en","en")):
                cid=uid("name:"+e["id"]+":"+lang)
                vid=uid("version:"+d["provenance"]["git_blob_sha"]+":"+e["id"]+":"+lang)
                conn.execute("INSERT INTO knowledge.claim(id) VALUES(%s) ON CONFLICT DO NOTHING",(cid,))
                conn.execute("""INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language,verification_status,scientific_note)
                    VALUES(%s,%s,%s,'NAME',%s,%s,'review_required',%s) ON CONFLICT(id) DO NOTHING""",
                    (vid,cid,eid,e[key],lang,e["precision"] if lang=="ar" else None))
                row=conn.execute("SELECT claim_id,subject_id,object_text,language FROM knowledge.claim_version WHERE id=%s",(vid,)).fetchone()
                if row!=(cid,eid,e[key],lang):
                    raise ValueError("existing version differs")
                conn.execute("INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator,stance) VALUES(%s,%s,%s,%s,'context') ON CONFLICT DO NOTHING",
                    (uid("evidence:"+str(vid)),vid,source_id,"entities/"+e["id"]+"/"+key))
                if lang=="ar":
                    conn.execute("""INSERT INTO knowledge.geometry_attestation(id,version_id,role,geom,precision_label,derivation)
                    VALUES(%s,%s,'location',ST_SetSRID(ST_MakePoint(%s,%s),4326),%s,%s) ON CONFLICT DO NOTHING""",
                    (uid("geometry:"+str(vid)),vid,e["lon"],e["lat"],e["precision"],"legacy entity location, not independently verified"))
                versions.append(vid)
    return versions


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage",action="store_true",required=True)
    p.parse_args()
    with psycopg.connect(os.environ["SATAC_IMPORT_DSN"]) as conn:
        ids=import_sample(conn)
    print(json.dumps({"staged_versions":[str(v) for v in ids]},ensure_ascii=False))


if __name__=="__main__":
    main()
