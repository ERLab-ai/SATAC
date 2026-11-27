"""SATAC public read API candidate. Never connects as database owner."""
import json
import os
import re
from contextlib import contextmanager
from decimal import Decimal
from typing import Literal
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

app = FastAPI(title="SATAC Public API", version="0.14.0-dev", description="Release-scoped public knowledge; astronomical years are decimal strings.")
YEAR = re.compile(r"^-?[0-9]{1,31}$")
MAX_YEAR = 10**30


@app.exception_handler(RequestValidationError)
def invalid_request(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {"code": "invalid_request", "message": "Invalid query parameters"}})


@app.exception_handler(HTTPException)
def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": str(exc.detail)}})


@app.exception_handler(psycopg.Error)
def database_error(request: Request, exc: psycopg.Error):
    return JSONResponse(status_code=503, content={"error": {"code": "database_unavailable"}})


@contextmanager
def reader():
    # Separate login inheriting only satac_reader; DB role assertions prevent owner connections.
    dsn = os.environ.get("SATAC_READER_DSN")
    if not dsn:
        raise HTTPException(503, "database_unavailable")
    with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5) as conn:
        with conn.transaction():
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            conn.execute("SET LOCAL statement_timeout = '5s'")
            privileges = conn.execute("""SELECT pg_has_role(current_user,'satac_reader','USAGE') AS reader,
                pg_has_role(current_user,'satac_publisher','MEMBER') AS publisher,
                pg_has_role(current_user,'satac_curator','MEMBER') AS curator,
                has_schema_privilege(current_user,'knowledge','USAGE') AS private_access,
                (SELECT rolsuper OR rolcreaterole OR rolcreatedb OR rolbypassrls FROM pg_roles WHERE rolname=current_user) AS elevated""").fetchone()
            if not privileges["reader"] or any(privileges[k] for k in ("publisher","curator","private_access","elevated")):
                raise HTTPException(503, "reader_configuration_invalid")
            yield conn


def resolve_release(conn, release):
    row = conn.execute(
        "SELECT release_id FROM public_read.releases WHERE " + ("release_id=%s" if release is not None else "is_current"),
        (release,) if release is not None else (),
    ).fetchone()
    if row is None:
        raise HTTPException(404, "release_not_found")
    return row["release_id"]


def parse_year(value):
    if not YEAR.fullmatch(value) or abs(int(value)) > MAX_YEAR:
        raise HTTPException(422, "invalid_year")
    return Decimal(value)


def time_range(as_of, start, end, certainty):
    if as_of is not None and (start is not None or end is not None):
        raise HTTPException(422, "conflicting_time_filters")
    if (start is None) != (end is None):
        raise HTTPException(422, "both_time_bounds_required")
    if as_of is None and start is None:
        if certainty != "any":
            raise HTTPException(422, "certainty_requires_time")
        return None
    lo, hi = (parse_year(as_of), parse_year(as_of)) if as_of is not None else (parse_year(start), parse_year(end))
    if lo > hi:
        raise HTTPException(422, "invalid_time_range")
    return lo, hi


def decode_payload(raw):
    # Preserve all 31-digit year values, including numeric values with trailing decimal zeros.
    precise = json.loads(raw, parse_float=Decimal)
    result = json.loads(raw)
    if "temporal" in result:
        for key in ("start_low","start_high","end_low","end_high"):
            if key in precise["temporal"]:
                result["temporal"][key] = str(int(precise["temporal"][key]))
    return result


def parse_bbox(value):
    try:
        west, south, east, north = map(float, value.split(","))
    except (ValueError, TypeError):
        raise HTTPException(422, "invalid_bbox")
    if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south < north <= 90 and west != east):
        raise HTTPException(422, "invalid_bbox")
    # Split a viewport crossing the antimeridian; geometries themselves must already be normalized.
    if west < east:
        return [(west,south,east,north)]
    parts = [(w,south,e,north) for w,e in ((west,180),(-180,east)) if w < e]
    if not parts:
        raise HTTPException(422, "invalid_bbox")
    return parts


def query_claims(conn, release, after, limit, bounds, certainty, entity=None, direction="both", predicate=None, bbox=None, lens=None):
    if after is not None and release is None:
        raise HTTPException(422, "pagination_requires_release")
    rid = resolve_release(conn, release)
    conditions = ["release_id=%s"]
    args = [rid]
    if after is not None:
        conditions.append("version_id>%s")
        args.append(after)
    if entity is not None:
        conditions.append("payload->>'predicate' NOT IN ('NAME','ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY')")
        if direction == "out":
            conditions.append("payload->>'subject_id'=%s")
            args.append(str(entity))
        elif direction == "in":
            conditions.append("payload->>'object_id'=%s")
            args.append(str(entity))
        else:
            conditions.append("(payload->>'subject_id'=%s OR payload->>'object_id'=%s)")
            args.extend([str(entity),str(entity)])
    if predicate is not None:
        conditions.append("payload->>'predicate'=%s")
        args.append(predicate)
    if bounds is not None:
        conditions.append("public_read.temporal_match(payload->'temporal',%s,%s)=ANY(%s::text[])")
        args.extend([*bounds, ["possible","certain"] if certainty == "any" else [certainty]])
    if bbox is not None:
        boxes = parse_bbox(bbox)
        clauses = ["public.ST_Intersects(public.ST_GeomFromGeoJSON(g->'geometry'),public.ST_MakeEnvelope(%s,%s,%s,%s,4326))" for _ in boxes]
        geom_filter = "(g ? 'geometry') AND ("+" OR ".join(clauses)+")"
        geom_args = [x for box in boxes for x in box]
        if lens is not None:
            geom_filter += " AND g->>'role'=%s"
            geom_args.append(lens)
        # Only matching, already-public snapshot geometries; no join to private tables.
        selected = "(SELECT jsonb_agg(g ORDER BY ord) FROM jsonb_array_elements(coalesce(payload->'geometries','[]'::jsonb)) WITH ORDINALITY AS a(g,ord) WHERE "+geom_filter+")"
        sql = "SELECT version_id,payload::text AS raw,matched FROM (SELECT version_id,payload,"+selected+" AS matched FROM public_read.release_claims WHERE "+" AND ".join(conditions)+") s WHERE matched IS NOT NULL ORDER BY version_id LIMIT %s"
        params = [*geom_args,*args,limit+1]
    else:
        sql = "SELECT version_id,payload::text AS raw FROM public_read.release_claims WHERE "+" AND ".join(conditions)+" ORDER BY version_id LIMIT %s"
        params = [*args,limit+1]
    rows = conn.execute(sql,params).fetchall()
    page = rows[:limit]
    return rid,page,(str(page[-1]["version_id"]) if len(rows)>limit else None)


@app.get("/health")
def health():
    with reader() as conn:
        conn.execute("SELECT 1").fetchone()
    return {"status":"ok"}


@app.get("/api/v1/releases")
def releases(after: UUID | None = None, limit: int = Query(50,ge=1,le=200)):
    with reader() as conn:
        rows = conn.execute("SELECT * FROM public_read.releases "+("WHERE release_id>%s " if after else "")+"ORDER BY release_id LIMIT %s",([after,limit+1] if after else [limit+1])).fetchall()
    page=rows[:limit]
    return {"releases":page,"next_after":str(page[-1]["release_id"]) if len(rows)>limit else None}


@app.get("/api/v1/claims/{claim_id}")
def claim(claim_id: UUID, release: UUID | None = None):
    with reader() as conn:
        rid=resolve_release(conn,release)
        row=conn.execute("SELECT payload::text AS raw FROM public_read.release_claims WHERE release_id=%s AND payload->>'claim_id'=%s",(rid,str(claim_id))).fetchone()
    if row is None:
        raise HTTPException(404,"claim_not_found")
    return {"release_id":str(rid),"claim":decode_payload(row["raw"])}


@app.get("/api/v1/relations")
def relations(entity_id: UUID, direction: Literal["in","out","both"]="both", predicate: str | None=Query(None,max_length=64),
              release: UUID | None=None, after: UUID | None=None, limit: int=Query(50,ge=1,le=200),
              as_of: str | None=Query(None,max_length=32), start: str | None=Query(None,alias="from",max_length=32),
              end: str | None=Query(None,alias="to",max_length=32), certainty: Literal["any","possible","certain"]="any",
              max_depth: int=Query(1,ge=1,le=1)):
    bounds=time_range(as_of,start,end,certainty)
    with reader() as conn:
        rid,rows,cursor=query_claims(conn,release,after,limit,bounds,certainty,entity_id,direction,predicate)
    return {"release_id":str(rid),"claims":[decode_payload(r["raw"]) for r in rows],"next_after":cursor}


@app.get("/api/v1/map/features")
def map_features(bbox: str=Query(...,max_length=120), release: UUID | None=None, after: UUID | None=None,
                 limit: int=Query(50,ge=1,le=200), as_of: str | None=Query(None,max_length=32),
                 start: str | None=Query(None,alias="from",max_length=32),end: str | None=Query(None,alias="to",max_length=32),
                 certainty: Literal["any","possible","certain"]="any",
                 lens: Literal["location","sovereignty","administration","influence","claim","trade","distribution"] | None=None):
    bounds=time_range(as_of,start,end,certainty)
    with reader() as conn:
        rid,rows,cursor=query_claims(conn,release,after,limit,bounds,certainty,bbox=bbox,lens=lens)
    features=[]
    for row in rows:
        p=decode_payload(row["raw"])
        for g in row["matched"]:
            features.append({"type":"Feature","geometry":g["geometry"],"properties":{
                "claim_id":p["claim_id"],"version_id":p["version_id"],"subject_id":p["subject_id"],
                "predicate":p["predicate"],**({"object_id":p["object_id"]} if "object_id" in p else {"name":p["object_text"]}),"role":g["role"],
                "precision":g["precision"],**({"uncertainty_m":g["uncertainty_m"]} if "uncertainty_m" in g else {})}})
    return {"type":"FeatureCollection","release_id":str(rid),"features":features,"next_after":cursor}


@app.get("/api/v1/entities/{entity_id}")
def entity_detail(entity_id: UUID, release: UUID | None=None):
    with reader() as conn:
        rid=resolve_release(conn,release)
        rows=conn.execute("""SELECT claim_id,version_id,name,lang,kind FROM public_read.entity_names
            WHERE release_id=%s AND entity_id=%s ORDER BY CASE lang WHEN 'ar' THEN 0 ELSE 1 END,version_id LIMIT 200""",(rid,entity_id)).fetchall()
    if not rows:
        raise HTTPException(404,"entity_not_found")
    return {"release_id":str(rid),"entity_id":str(entity_id),"kind":rows[0]["kind"],
            "names":[{k:v for k,v in r.items() if k!="kind"} for r in rows]}


@app.get("/api/v1/search")
def search(q: str=Query(...,min_length=1,max_length=120),lang: Literal["ar","en","any"]="any",
           kind: str | None=Query(None,alias="type",max_length=40),release: UUID | None=None,
           after: UUID | None=None,limit: int=Query(50,ge=1,le=200),
           as_of: str | None=Query(None,max_length=32),start: str | None=Query(None,alias="from",max_length=32),
           end: str | None=Query(None,alias="to",max_length=32),certainty: Literal["any","possible","certain"]="any"):
    bounds=time_range(as_of,start,end,certainty)
    if after is not None and release is None:
        raise HTTPException(422,"pagination_requires_release")
    with reader() as conn:
        key=conn.execute("SELECT public_read.search_key(%s) AS key",(q,)).fetchone()["key"]
        if not key:
            raise HTTPException(422,"empty_search")
        rid=resolve_release(conn,release)
        filters=["release_id=%s","strpos(public_read.search_key(name),%s)>0"]
        args=[rid,key]
        if lang!="any":
            filters.append("lang=%s");args.append(lang)
        if kind is not None:
            filters.append("kind=%s");args.append(kind)
        if after is not None:
            filters.append("version_id>%s");args.append(after)
        if bounds is not None:
            filters.append("public_read.temporal_match(temporal,%s,%s)=ANY(%s::text[])")
            args.extend([*bounds,["possible","certain"] if certainty=="any" else [certainty]])
        rows=conn.execute("SELECT entity_id,claim_id,version_id,name,lang,kind FROM public_read.entity_names WHERE "+" AND ".join(filters)+" ORDER BY version_id LIMIT %s",[*args,limit+1]).fetchall()
    page=rows[:limit]
    return {"release_id":str(rid),"results":page,"next_after":str(page[-1]["version_id"]) if len(rows)>limit else None}


@app.get("/api/v1/articles")
def articles(release: UUID | None=None,q: str | None=Query(None,max_length=120),
             era: Literal["all","deep","ancient","islamic","states","modern"]="all"):
    with reader() as conn:
        rid=resolve_release(conn,release)
        filters=["release_id=%s"];args=[rid]
        if era!="all":
            filters.append("article->'eras' ? %s");args.append(era)
        if q is not None:
            key=conn.execute("SELECT public_read.search_key(%s) AS key",(q,)).fetchone()["key"]
            if not key: raise HTTPException(422,"empty_search")
            filters.append("strpos(public_read.search_key(concat_ws(' ',article->>'title',article->>'subtitle',article->>'summary',article->>'keywords',article->>'sections')),%s)>0");args.append(key)
        rows=conn.execute("SELECT article FROM public_read.articles WHERE "+" AND ".join(filters)+" ORDER BY article->>'id' LIMIT 200",args).fetchall()
    keys=("id","title","subtitle","category","art","eras","location","summary","short_name","heritage_status")
    return {"release_id":str(rid),"articles":[{k:r["article"][k] for k in keys if k in r["article"]} for r in rows]}


@app.get("/api/v1/articles/{slug}")
def article(slug: str,release: UUID | None=None):
    if not re.fullmatch(r"[a-z0-9_]{1,80}",slug): raise HTTPException(404,"article_not_found")
    with reader() as conn:
        rid=resolve_release(conn,release)
        row=conn.execute("SELECT work_id,article FROM public_read.articles WHERE release_id=%s AND article->>'id'=%s",(rid,slug)).fetchone()
        if row is None: raise HTTPException(404,"article_not_found")
        titles={r["id"]:r["title"] for r in conn.execute("SELECT article->>'id' AS id,article->>'title' AS title FROM public_read.articles WHERE release_id=%s",(rid,))}
    a=row["article"]
    a["related"]=[s for s in a["related"] if s in titles]
    return {"release_id":str(rid),"work_id":str(row["work_id"]),"article":a,"related_topics":[{"id":s,"title":titles[s]} for s in a["related"]]}


@app.get("/api/v1/editorial-network")
def editorial_network(release: UUID | None=None):
    with reader() as conn:
        rid=resolve_release(conn,release)
        articles=[r["article"] for r in conn.execute("SELECT article FROM public_read.articles WHERE release_id=%s ORDER BY article->>'id'",(rid,))]
        nodes={a["id"]:{k:a[k] for k in ("id","title","location","art")} for a in articles}
        rows=conn.execute("SELECT kind,editorial FROM public_read.editorial_network WHERE release_id=%s ORDER BY (editorial->>'ordinal')::int,version_id",(rid,)).fetchall()
    links=[];journeys=[]
    for row in rows:
        item=row["editorial"]
        rec=item["record"]
        if row["kind"]=="EDITORIAL_LINK" and all(x in nodes for x in rec[:2]):
            links.append(item)
        elif row["kind"]=="EDITORIAL_JOURNEY" and all(x in nodes for x in rec["ids"]):
            journeys.append(item)
    return {"release_id":str(rid),"geometry_semantics":"editorial_connections_not_routes","articles":list(nodes.values()),"links":links,"journeys":journeys}


@app.get("/api/v1/directory")
def directory(release: UUID | None=None,collection: Literal["historical","modern","all"]="all",
              region: str | None=Query(None,max_length=120),q: str | None=Query(None,max_length=120)):
    with reader() as conn:
        rid=resolve_release(conn,release)
        filters=["release_id=%s"];args=[rid]
        if collection!="all":
            filters.append("directory->>'collection'=%s");args.append(collection)
        if region is not None:
            filters.append("directory->>'region_label'=%s");args.append(region)
        if q is not None:
            key=conn.execute("SELECT public_read.search_key(%s) AS key",(q,)).fetchone()["key"]
            if not key: raise HTTPException(422,"empty_search")
            filters.append("strpos(public_read.search_key(concat_ws(' ',directory->'record'->>'name',directory->'record'->>'en')),%s)>0");args.append(key)
        rows=conn.execute("SELECT entity_id,directory,references FROM public_read.directory WHERE "+" AND ".join(filters)+" ORDER BY directory->>'collection',directory->'record'->>'name',entity_id LIMIT 2001",args).fetchall()
    return {"release_id":str(rid),"entries":[{"entity_id":str(r["entity_id"]),**r["directory"],"references":r["references"]} for r in rows[:2000]],"truncated":len(rows)>2000}
