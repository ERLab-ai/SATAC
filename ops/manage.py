"""Privileged one-shot operations; never shipped in public API image."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from uuid import UUID
import psycopg
from psycopg import sql

ROOT=Path(__file__).resolve().parents[1]

def secret(name):
    value=Path("/run/secrets",name).read_text(encoding="utf-8").rstrip("\r\n")
    if len(value)<32 or any(c in value for c in "\r\n\x00"):
        raise ValueError("invalid deployment secret")
    return value

def connection():
    return psycopg.connect(host="db",dbname="satac",user="satac_admin",
                           password=secret("admin_password"),connect_timeout=10)

def migrations():
    result=[]
    for path in sorted((ROOT/"db/migrations").glob("*.sql")):
        raw=path.read_bytes()
        s=raw.decode("utf-8")
        if not re.match(r"\A(?:--[^\n]*\n|\s)*BEGIN;\s*",s) or not re.search(r"\nCOMMIT;\s*\Z",s):
            raise ValueError("migration transaction wrapper mismatch: "+path.name)
        body=re.sub(r"\A(?:--[^\n]*\n|\s)*BEGIN;\s*","",s,count=1)
        body=re.sub(r"\nCOMMIT;\s*\Z","",body,count=1)
        result.append((path.name,hashlib.sha256(raw).hexdigest(),body))
    if not result or [int(x[0][:4]) for x in result]!=list(range(1,len(result)+1)):
        raise ValueError("migration sequence gap")
    return result

def migrate(conn):
    planned=migrations()
    conn.autocommit=True
    conn.execute("SELECT pg_advisory_lock(716050)")
    try:
        with conn.transaction():
            if conn.execute("SELECT to_regclass('satac_ops.schema_migrations')").fetchone()[0] is None:
                if conn.execute("SELECT to_regnamespace('knowledge')").fetchone()[0] is not None:
                    raise RuntimeError("existing untracked schema")
                conn.execute("CREATE SCHEMA satac_ops")
                conn.execute("REVOKE ALL ON SCHEMA satac_ops FROM PUBLIC")
                conn.execute("CREATE TABLE satac_ops.schema_migrations(name text PRIMARY KEY,sha256 text NOT NULL,applied_at timestamptz NOT NULL DEFAULT clock_timestamp())")
        existing=conn.execute("SELECT name,sha256 FROM satac_ops.schema_migrations ORDER BY name").fetchall()
        if existing!=[(n,h) for n,h,_ in planned[:len(existing)]]:
            raise RuntimeError("migration history drift or downgrade")
        for name,digest,body in planned[len(existing):]:
            with conn.transaction():
                conn.execute(body,prepare=False)
                conn.execute("INSERT INTO satac_ops.schema_migrations(name,sha256) VALUES(%s,%s)",(name,digest))
        with conn.transaction():
            role=conn.execute("SELECT rolcanlogin,rolsuper,rolcreaterole,rolcreatedb,rolreplication,rolbypassrls,rolinherit FROM pg_roles WHERE rolname='satac_runtime'").fetchone()
            if role is None:
                conn.execute("CREATE ROLE satac_runtime LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS")
            elif role!=(True,False,False,False,False,False,True):
                raise RuntimeError("unexpected runtime role attributes")
            conn.execute("GRANT satac_reader TO satac_runtime")
            memberships=conn.execute("SELECT rolname FROM pg_roles WHERE rolname<>'satac_runtime' AND pg_has_role('satac_runtime',oid,'MEMBER') ORDER BY rolname").fetchall()
            if memberships!=[("satac_reader",)] or conn.execute("SELECT has_schema_privilege('satac_runtime','knowledge','USAGE')").fetchone()[0]:
                raise RuntimeError("unexpected runtime privileges")
            conn.execute(sql.SQL("ALTER ROLE satac_runtime PASSWORD {}").format(sql.Literal(secret("reader_password"))))
        return {"applied":len(planned),"new":len(planned)-len(existing)}
    finally:
        conn.execute("SELECT pg_advisory_unlock(716050)")

def digest_projection(conn,ids):
    value=conn.execute("""SELECT encode(public.digest(convert_to(jsonb_agg(knowledge.project(x) ORDER BY x)::text,'UTF8'),'sha256'),'hex')
        FROM unnest(%s::uuid[]) x""",(ids,)).fetchone()[0]
    if not value: raise ValueError("empty proposal")
    return value

def stage(conn):
    from pipelines.import_genesis_places import import_sample
    from pipelines import import_encyclopedia,import_editorial_network,import_directory,import_routes,import_snapshots,import_geology,import_cells,import_extended_topics
    ids=[]
    with conn.transaction():
        for importer in (import_sample,import_encyclopedia.stage,import_editorial_network.stage,import_directory.stage,
                         import_routes.stage,import_snapshots.stage,import_geology.stage,import_cells.stage,import_extended_topics.stage):
            ids.extend(importer(conn))
        ids=sorted(ids)
        if len(ids)!=3309 or len(set(ids))!=len(ids):
            raise ValueError("unexpected restored candidate membership")
        return {"format":"satac-initial-proposal-v1","version_ids":[str(x) for x in ids],
                "projection_sha256":digest_projection(conn,ids)}

def publish_initial(conn,args):
    raw=sys.stdin.buffer.read(2_000_001)
    if len(raw)>2_000_000 or hashlib.sha256(raw).hexdigest()!=args.manifest_sha256:
        raise ValueError("proposal digest mismatch")
    proposal=json.loads(raw)
    if proposal.get("format")!="satac-initial-proposal-v1":
        raise ValueError("invalid proposal")
    ids=[UUID(x) for x in proposal["version_ids"]]
    if len(ids)!=3309 or ids!=sorted(set(ids)):
        raise ValueError("invalid initial membership")
    # Acquire the session lock before taking a repeatable-read snapshot.
    conn.autocommit=True
    conn.execute("SELECT pg_advisory_lock(716032)")
    try:
        with conn.transaction():
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            if conn.execute("SELECT EXISTS(SELECT 1 FROM knowledge.release)").fetchone()[0]:
                raise RuntimeError("initial publication only")
            if digest_projection(conn,ids)!=proposal["projection_sha256"]:
                raise ValueError("staged projection changed")
            conn.execute("SET LOCAL ROLE satac_publisher")
            digest=conn.execute("SELECT knowledge.publish(%s,%s)",(args.release,ids)).fetchone()[0]
            if digest!=proposal["projection_sha256"] or conn.execute("SELECT knowledge.verify_release(%s)",(args.release,)).fetchone()[0] is not True:
                raise RuntimeError("publication digest mismatch")
            return {"release_id":str(args.release),"manifest_sha256":digest,"members":len(ids)}
    finally:
        conn.execute("SELECT pg_advisory_unlock(716032)")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("migrate")
    sub.add_parser("stage")
    pub=sub.add_parser("publish-initial")
    pub.add_argument("--manifest-sha256",required=True)
    pub.add_argument("--release",required=True,type=UUID)
    activate=sub.add_parser("activate-release")
    activate.add_argument("--expected-current",required=True,type=UUID)
    activate.add_argument("--target",required=True,type=UUID)
    activate.add_argument("--manifest-sha256",required=True)
    activate.add_argument("--reason",required=True)
    activate.add_argument("--actor",required=True)
    embedded=sub.add_parser("revoke-embedded-source")
    embedded.add_argument("--source",required=True,type=UUID)
    embedded.add_argument("--reason",required=True)
    embedded.add_argument("--actor",required=True)
    asset=sub.add_parser("revoke-asset")
    asset.add_argument("--path",required=True)
    asset.add_argument("--reason",required=True)
    asset.add_argument("--actor",required=True)
    url=sub.add_parser("revoke-embedded-url")
    url.add_argument("--url",required=True)
    url.add_argument("--reason",required=True)
    url.add_argument("--actor",required=True)
    identity=sub.add_parser("assert-external-identity")
    identity.add_argument("--entity",required=True,type=UUID)
    identity.add_argument("--namespace",required=True)
    identity.add_argument("--external-id",required=True)
    identity.add_argument("--source",required=True,type=UUID)
    identity.add_argument("--locator")
    identity.add_argument("--actor",required=True)
    proposal=sub.add_parser("propose-identity")
    proposal.add_argument("--entity-a",required=True,type=UUID)
    proposal.add_argument("--entity-b",required=True,type=UUID)
    proposal.add_argument("--reason",required=True)
    proposal.add_argument("--actor",required=True)
    decision=sub.add_parser("decide-identity")
    decision.add_argument("--candidate",required=True,type=UUID)
    decision.add_argument("--expected",type=UUID)
    decision.add_argument("--decision",required=True,choices=("same_entity","distinct_entities","undetermined"))
    decision.add_argument("--reason",required=True)
    decision.add_argument("--reviewer",required=True)
    decision.add_argument("--source",type=UUID)
    decision.add_argument("--locator")
    review=sub.add_parser("record-claim-review")
    review.add_argument("--version",required=True,type=UUID)
    review.add_argument("--expected",type=UUID)
    review.add_argument("--decision",required=True,choices=("verified","review_required","disputed","known_incorrect"))
    review.add_argument("--reason",required=True)
    review.add_argument("--reviewer",required=True)
    link=sub.add_parser("stage-identity-link")
    link.add_argument("--decision",required=True,type=UUID)
    link.add_argument("--alias",required=True,type=UUID)
    link.add_argument("--canonical",required=True,type=UUID)
    a=p.parse_args()
    with connection() as conn:
        if a.command=="migrate":result=migrate(conn)
        elif a.command=="stage":result=stage(conn)
        elif a.command=="publish-initial":result=publish_initial(conn,a)
        elif a.command=="stage-identity-link":
            with conn.transaction():
                conn.execute("SET LOCAL ROLE satac_curator")
                v=conn.execute("SELECT knowledge.stage_identity_link(%s,%s,%s)",(a.decision,a.alias,a.canonical)).fetchone()[0]
                result={"operation":a.command,"version_id":str(v)}
        elif a.command in ("assert-external-identity","propose-identity","decide-identity","record-claim-review"):
            with conn.transaction():
                conn.execute("SET LOCAL ROLE satac_curator")
                if a.command=="assert-external-identity":
                    value=conn.execute("SELECT knowledge.assert_external_identity(%s,%s,%s,%s,%s,%s)",
                        (a.entity,a.namespace,a.external_id,a.source,a.locator,a.actor)).fetchone()[0]
                elif a.command=="propose-identity":
                    value=conn.execute("SELECT knowledge.propose_identity(%s,%s,%s,%s)",
                        (a.entity_a,a.entity_b,a.reason,a.actor)).fetchone()[0]
                elif a.command=="decide-identity":
                    value=conn.execute("SELECT knowledge.decide_identity(%s,%s,%s,%s,%s,%s,%s)",
                        (a.candidate,a.expected,a.decision,a.reason,a.reviewer,a.source,a.locator)).fetchone()[0]
                else:
                    value=conn.execute("SELECT knowledge.record_claim_review(%s,%s,%s,%s,%s)",
                        (a.version,a.expected,a.decision,a.reason,a.reviewer)).fetchone()[0]
                result={"operation":a.command,"id":str(value)}
        elif a.command=="revoke-embedded-url":
            with conn.transaction():
                conn.execute("SET LOCAL ROLE satac_curator")
                conn.execute("SELECT knowledge.revoke_embedded_url(%s,%s,%s)",(a.url,a.reason,a.actor))
                result={"recorded":True,"operation":a.command}
        elif a.command=="revoke-asset":
            with conn.transaction():
                conn.execute("SET LOCAL ROLE satac_curator")
                conn.execute("SELECT knowledge.revoke_asset(%s,%s,%s)",(a.path,a.reason,a.actor))
                result={"recorded":True,"operation":a.command}
        elif a.command=="revoke-embedded-source":
            with conn.transaction():
                conn.execute("SET LOCAL ROLE satac_curator")
                conn.execute("SELECT knowledge.revoke_embedded_source(%s,%s,%s)",(a.source,a.reason,a.actor))
                result={"recorded":True,"operation":a.command}
        else:
            with conn.transaction():
                conn.execute("SET LOCAL ROLE satac_publisher")
                event=conn.execute("SELECT knowledge.activate_release(%s,%s,%s,%s,%s)",
                    (a.expected_current,a.target,a.manifest_sha256,a.reason,a.actor)).fetchone()[0]
                result={"activation_id":str(event),"release_id":str(a.target)}
    print(json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    main()
