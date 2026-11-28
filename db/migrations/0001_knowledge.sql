-- P0/P1 candidate, install once on a fresh PostgreSQL 16/PostGIS database.
BEGIN;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA knowledge;
CREATE SCHEMA public_read;
CREATE ROLE satac_reader NOLOGIN;
CREATE ROLE satac_publisher NOLOGIN;
CREATE ROLE satac_curator NOLOGIN;
REVOKE ALL ON SCHEMA knowledge FROM PUBLIC;
REVOKE ALL ON SCHEMA public_read FROM PUBLIC;

CREATE TABLE knowledge.entity (
 id uuid PRIMARY KEY,
 kind text NOT NULL CHECK (kind IN ('Place','Person','Community','Polity','Event','Route','Institution','Work','Manuscript','Artifact','Concept'))
);
CREATE TABLE knowledge.predicate (
 code text PRIMARY KEY, domain_types text[] NOT NULL, range_types text[] NOT NULL,
 requires_justification boolean NOT NULL DEFAULT false
);
INSERT INTO knowledge.predicate VALUES
 ('LOCATED_IN',ARRAY['Place','Institution','Artifact','Manuscript','Event'],ARRAY['Place'],false),
 ('BORN_IN',ARRAY['Person'],ARRAY['Place'],false),
 ('LIVED_IN',ARRAY['Person','Community'],ARRAY['Place'],false),
 ('TRAVELED_TO',ARRAY['Person','Community'],ARRAY['Place'],false),
 ('TRADED_WITH',ARRAY['Place','Community','Polity','Institution','Person'],ARRAY['Place','Community','Polity','Institution','Person'],false),
 ('GOVERNED_BY',ARRAY['Place','Community','Polity','Institution'],ARRAY['Polity','Person','Institution'],false),
 ('AUTHORED',ARRAY['Person','Community','Institution'],ARRAY['Work'],false),
 ('FOUNDED',ARRAY['Person','Community','Polity','Institution'],ARRAY['Place','Polity','Institution'],false),
 ('STUDIED_UNDER',ARRAY['Person'],ARRAY['Person'],false),
 ('PARTICIPATED_IN',ARRAY['Person','Community','Polity','Institution'],ARRAY['Event'],false),
 ('CONNECTED_TO',ARRAY['*'],ARRAY['*'],false),
 ('INFLUENCED',ARRAY['*'],ARRAY['*'],true),
 ('ATTESTED_BY',ARRAY['*'],ARRAY['Artifact','Manuscript','Work'],false);

CREATE TABLE knowledge.claim (id uuid PRIMARY KEY);
CREATE TABLE knowledge.claim_version (
 id uuid PRIMARY KEY,
 claim_id uuid NOT NULL REFERENCES knowledge.claim,
 supersedes_id uuid UNIQUE,
 subject_id uuid NOT NULL REFERENCES knowledge.entity,
 predicate text NOT NULL REFERENCES knowledge.predicate,
 object_id uuid NOT NULL REFERENCES knowledge.entity,
 verification_status text NOT NULL DEFAULT 'unreviewed' CHECK (verification_status IN ('unreviewed','review_required','verified','disputed','known_incorrect')),
 epistemic_status text NOT NULL DEFAULT 'uncertain' CHECK (epistemic_status IN ('well_supported','plausible','disputed','uncertain','unsupported')),
 scientific_note text,
 justification text,
 synthetic boolean NOT NULL DEFAULT false,
 restricted boolean NOT NULL DEFAULT false,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE (id, claim_id),
 FOREIGN KEY (supersedes_id, claim_id) REFERENCES knowledge.claim_version(id, claim_id),
 CHECK (supersedes_id IS DISTINCT FROM id)
);
CREATE UNIQUE INDEX one_root_per_claim ON knowledge.claim_version(claim_id) WHERE supersedes_id IS NULL;
CREATE FUNCTION knowledge.validate_relation() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,knowledge AS $$
 DECLARE p knowledge.predicate; s text; o text;
 BEGIN
 SELECT * INTO STRICT p FROM knowledge.predicate WHERE code=NEW.predicate;
 SELECT kind INTO STRICT s FROM knowledge.entity WHERE id=NEW.subject_id;
 SELECT kind INTO STRICT o FROM knowledge.entity WHERE id=NEW.object_id;
 IF NOT (s=ANY(p.domain_types) OR '*'=ANY(p.domain_types)) OR
    NOT (o=ANY(p.range_types) OR '*'=ANY(p.range_types)) OR
    (p.requires_justification AND nullif(btrim(NEW.justification),'') IS NULL)
 THEN RAISE EXCEPTION 'invalid relation' USING ERRCODE='23514'; END IF;
 RETURN NEW;
 END $$;
CREATE TRIGGER relation_check BEFORE INSERT ON knowledge.claim_version FOR EACH ROW EXECUTE FUNCTION knowledge.validate_relation();

-- Astronomical integer years, no calendar conversion; numeric storage ceiling documented.
CREATE FUNCTION knowledge.valid_bound(k text, lo numeric, hi numeric) RETURNS boolean
 LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT CASE WHEN k='bounded' THEN lo IS NOT NULL AND hi IS NOT NULL
 AND lo BETWEEN -1e30::numeric AND 1e30::numeric AND hi BETWEEN -1e30::numeric AND 1e30::numeric
 AND lo=trunc(lo) AND hi=trunc(hi) AND lo<=hi
 WHEN k IN ('open','unknown') THEN lo IS NULL AND hi IS NULL ELSE false END $$;
CREATE TABLE knowledge.temporal_extent (
 version_id uuid PRIMARY KEY REFERENCES knowledge.claim_version,
 start_kind text NOT NULL, start_low numeric, start_high numeric,
 end_kind text NOT NULL, end_low numeric, end_high numeric,
 original_text text NOT NULL CHECK (btrim(original_text)<>''),
 calendar text NOT NULL CHECK (btrim(calendar)<>''),
 precision_label text NOT NULL CHECK (btrim(precision_label)<>''),
 normalization_method text NOT NULL CHECK (btrim(normalization_method)<>''),
 CHECK (knowledge.valid_bound(start_kind,start_low,start_high)),
 CHECK (knowledge.valid_bound(end_kind,end_low,end_high)),
 CHECK (start_kind<>'bounded' OR end_kind<>'bounded' OR start_low<=end_high)
);
CREATE FUNCTION knowledge.temporal_match(t knowledge.temporal_extent, qlo numeric, qhi numeric) RETURNS text
 LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
 BEGIN
 IF qlo IS NULL OR qhi IS NULL OR qlo NOT BETWEEN -1e30::numeric AND 1e30::numeric OR qhi NOT BETWEEN -1e30::numeric AND 1e30::numeric OR qlo<>trunc(qlo) OR qhi<>trunc(qhi) OR qlo>qhi THEN
 RAISE EXCEPTION 'invalid query years' USING ERRCODE='22023'; END IF;
 IF t.start_kind='unknown' AND t.end_kind='unknown' THEN RETURN 'undated'; END IF;
 IF (t.start_kind='bounded' AND t.start_low>qhi) OR (t.end_kind='bounded' AND t.end_high<qlo) THEN RETURN 'none'; END IF;
 IF t.start_kind='unknown' OR t.end_kind='unknown' THEN RETURN 'possible'; END IF;
 IF (t.start_kind='open' OR t.start_high<=qhi OR (t.end_kind='bounded' AND t.end_high<=qhi))
 AND (t.end_kind='open' OR t.end_low>=qlo OR (t.start_kind='bounded' AND t.start_low>=qlo))
 THEN RETURN 'certain'; END IF;
 RETURN 'possible';
 END $$;

CREATE TABLE knowledge.geometry_attestation (
 id uuid PRIMARY KEY, version_id uuid NOT NULL REFERENCES knowledge.claim_version,
 role text NOT NULL CHECK (role IN ('location','sovereignty','administration','influence','claim','trade','distribution')),
 geom public.geometry(Geometry,4326), precision_label text NOT NULL CHECK(btrim(precision_label)<>''),
 derivation text NOT NULL CHECK(btrim(derivation)<>''),
 uncertainty_m numeric CHECK(uncertainty_m>=0 AND uncertainty_m<1e12),
 restricted boolean NOT NULL DEFAULT false,
 CHECK (geom IS NULL OR (public.ST_NDims(geom)=2 AND NOT public.ST_IsEmpty(geom) AND public.ST_IsValid(geom)
 AND public.ST_XMin(geom)>=-180 AND public.ST_XMax(geom)<=180 AND public.ST_YMin(geom)>=-90 AND public.ST_YMax(geom)<=90))
);
CREATE INDEX geometry_gist ON knowledge.geometry_attestation USING gist(geom);

CREATE TABLE knowledge.source_version (
 id uuid PRIMARY KEY, title text NOT NULL CHECK(btrim(title)<>''),
 content_sha256 text CHECK(content_sha256 ~ '^[0-9a-f]{64}$'),
 retrieved_at timestamptz, restricted boolean NOT NULL DEFAULT false
);
CREATE TABLE knowledge.evidence (
 id uuid PRIMARY KEY, version_id uuid NOT NULL REFERENCES knowledge.claim_version,
 source_version_id uuid NOT NULL REFERENCES knowledge.source_version,
 locator text CHECK(locator IS NULL OR btrim(locator)<>''),
 stance text NOT NULL DEFAULT 'context' CHECK (stance IN ('supports','contradicts','context')),
 independence_group text
);
CREATE TABLE knowledge.review (
 id uuid PRIMARY KEY, version_id uuid NOT NULL REFERENCES knowledge.claim_version,
 reviewer text NOT NULL CHECK(btrim(reviewer)<>''), decision text NOT NULL, rationale text NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE knowledge.review_task (
 version_id uuid NOT NULL REFERENCES knowledge.claim_version,
 reason text NOT NULL CHECK(reason IN ('documentation','review','correction')),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(), resolved_at timestamptz,
 PRIMARY KEY(version_id,reason)
);
CREATE FUNCTION knowledge.queue_tasks() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,knowledge AS $$
 BEGIN
 INSERT INTO knowledge.review_task(version_id,reason) VALUES(NEW.id,'documentation');
 IF NEW.verification_status IN ('unreviewed','review_required','disputed') THEN
 INSERT INTO knowledge.review_task(version_id,reason) VALUES(NEW.id,'review'); END IF;
 IF NEW.verification_status='known_incorrect' THEN
 INSERT INTO knowledge.review_task(version_id,reason) VALUES(NEW.id,'correction'); END IF;
 RETURN NEW;
 END $$;
CREATE TRIGGER followup AFTER INSERT ON knowledge.claim_version FOR EACH ROW EXECUTE FUNCTION knowledge.queue_tasks();
CREATE FUNCTION knowledge.refresh_documentation() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,knowledge AS $$
 BEGIN
 UPDATE knowledge.review_task SET resolved_at=CASE WHEN EXISTS
 (SELECT 1 FROM knowledge.evidence WHERE version_id=NEW.version_id AND locator IS NULL)
 THEN NULL ELSE clock_timestamp() END WHERE version_id=NEW.version_id AND reason='documentation';
 RETURN NEW;
 END $$;
CREATE TRIGGER evidence_followup AFTER INSERT ON knowledge.evidence FOR EACH ROW EXECUTE FUNCTION knowledge.refresh_documentation();

CREATE TABLE knowledge.release (
 id uuid PRIMARY KEY, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 manifest_sha256 text NOT NULL CHECK(manifest_sha256 ~ '^[0-9a-f]{64}$')
);
CREATE TABLE knowledge.release_member (
 release_id uuid NOT NULL REFERENCES knowledge.release,
 version_id uuid NOT NULL REFERENCES knowledge.claim_version,
 payload jsonb NOT NULL,
 PRIMARY KEY(release_id,version_id)
);
CREATE TABLE knowledge.current_release (singleton boolean PRIMARY KEY CHECK(singleton), release_id uuid NOT NULL REFERENCES knowledge.release);
CREATE TABLE knowledge.withdrawal (
 version_id uuid PRIMARY KEY REFERENCES knowledge.claim_version,
 reason text NOT NULL CHECK(btrim(reason)<>''), actor text NOT NULL CHECK(btrim(actor)<>''),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE knowledge.correction (
 old_id uuid PRIMARY KEY REFERENCES knowledge.claim_version,
 new_id uuid UNIQUE NOT NULL REFERENCES knowledge.claim_version,
 reason text NOT NULL CHECK(btrim(reason)<>''), basis text NOT NULL CHECK(btrim(basis)<>''),
 actor text NOT NULL CHECK(btrim(actor)<>''), recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

-- Snapshot public content (explicit allowlist), never administrative columns or restricted references.
CREATE FUNCTION knowledge.project(v uuid) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog,knowledge,public AS $$
 SELECT jsonb_strip_nulls(jsonb_build_object(
 'claim_id',c.claim_id,'version_id',c.id,'subject_id',c.subject_id,'predicate',c.predicate,'object_id',c.object_id,
 'scientific_note',c.scientific_note,
 'temporal',(SELECT to_jsonb(t)-'version_id' FROM knowledge.temporal_extent t WHERE t.version_id=c.id),
 'geometries',(SELECT jsonb_agg(jsonb_strip_nulls(jsonb_build_object('role',g.role,'geometry',public.ST_AsGeoJSON(g.geom,15)::jsonb,'precision',g.precision_label,'uncertainty_m',g.uncertainty_m)) ORDER BY g.id)
 FROM knowledge.geometry_attestation g WHERE g.version_id=c.id AND NOT g.restricted),
 'references',(SELECT jsonb_agg(jsonb_strip_nulls(jsonb_build_object('source_version_id',s.id,'title',s.title,'locator',e.locator,'stance',e.stance)) ORDER BY e.id)
 FROM knowledge.evidence e JOIN knowledge.source_version s ON s.id=e.source_version_id WHERE e.version_id=c.id AND NOT s.restricted)
 )) FROM knowledge.claim_version c WHERE c.id=v $$;

CREATE FUNCTION knowledge.publish(r uuid, ids uuid[]) RETURNS text LANGUAGE plpgsql SECURITY DEFINER
 SET search_path=pg_catalog,knowledge,public AS $$
 DECLARE h text;
 BEGIN
 PERFORM pg_advisory_xact_lock(716032);
 IF r IS NULL OR ids IS NULL OR array_position(ids,NULL) IS NOT NULL OR
 (SELECT count(DISTINCT x) FROM unnest(ids) x)<>cardinality(ids) OR
 (SELECT count(DISTINCT claim_id) FROM knowledge.claim_version WHERE id=ANY(ids))<>cardinality(ids)
 OR EXISTS(SELECT 1 FROM knowledge.claim_version c WHERE c.id=ANY(ids) AND
 (c.synthetic OR c.restricted OR c.verification_status='known_incorrect' OR EXISTS(SELECT 1 FROM knowledge.withdrawal w WHERE w.version_id=c.id)))
 THEN RAISE EXCEPTION 'invalid release membership' USING ERRCODE='23514'; END IF;
 -- Materialize once so hash and members use the same snapshot even if staging changes concurrently.
 WITH snapshot AS MATERIALIZED (SELECT x AS id,knowledge.project(x) AS payload FROM unnest(ids) x),
 inserted AS (INSERT INTO knowledge.release(id,manifest_sha256)
 SELECT r,encode(public.digest(convert_to(coalesce(jsonb_agg(payload ORDER BY id),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') FROM snapshot RETURNING manifest_sha256),
 members AS (INSERT INTO knowledge.release_member SELECT r,s.id,s.payload FROM snapshot s CROSS JOIN inserted RETURNING version_id)
 SELECT manifest_sha256 INTO h FROM inserted;
 INSERT INTO knowledge.current_release VALUES(true,r) ON CONFLICT(singleton) DO UPDATE SET release_id=excluded.release_id;
 RETURN h;
 END $$;
CREATE FUNCTION knowledge.flag_incorrect(v uuid, reason_text text, actor_text text) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
 SET search_path=pg_catalog,knowledge AS $$
 BEGIN
 PERFORM pg_advisory_xact_lock(716032);
 INSERT INTO knowledge.withdrawal(version_id,reason,actor) VALUES(v,reason_text,actor_text) ON CONFLICT DO NOTHING;
 INSERT INTO knowledge.review_task(version_id,reason) VALUES(v,'correction') ON CONFLICT(version_id,reason) DO UPDATE SET resolved_at=NULL;
 END $$;
-- Replacement is staged first. Same claim, same visibility, successor of old version.
CREATE FUNCTION knowledge.correct(old_v uuid,new_v uuid,r uuid,reason_text text,basis_text text,actor_text text)
 RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,knowledge AS $$
 DECLARE a knowledge.claim_version; b knowledge.claim_version; ids uuid[]; active uuid; h text;
 BEGIN
 PERFORM pg_advisory_xact_lock(716032);
 SELECT * INTO STRICT a FROM knowledge.claim_version WHERE id=old_v;
 SELECT * INTO STRICT b FROM knowledge.claim_version WHERE id=new_v;
 IF b.supersedes_id IS DISTINCT FROM a.id OR b.claim_id<>a.claim_id OR b.synthetic<>a.synthetic OR b.restricted<>a.restricted
 OR b.verification_status='known_incorrect' OR nullif(btrim(reason_text),'') IS NULL OR nullif(btrim(basis_text),'') IS NULL OR nullif(btrim(actor_text),'') IS NULL
 OR EXISTS(SELECT 1 FROM knowledge.withdrawal WHERE version_id=new_v)
 OR EXISTS(SELECT 1 FROM knowledge.claim_version WHERE supersedes_id=new_v)
 THEN RAISE EXCEPTION 'invalid correction' USING ERRCODE='23514'; END IF;
 SELECT release_id INTO active FROM knowledge.current_release;
 IF EXISTS(SELECT 1 FROM knowledge.release_member WHERE release_id=active AND version_id=old_v) THEN
 IF r IS NULL THEN RAISE EXCEPTION 'fresh release required' USING ERRCODE='23514'; END IF;
 SELECT array_agg(CASE WHEN m.version_id=old_v THEN new_v ELSE m.version_id END) INTO ids
 FROM knowledge.release_member m WHERE m.release_id=active AND (m.version_id=old_v OR NOT EXISTS(SELECT 1 FROM knowledge.withdrawal w WHERE w.version_id=m.version_id));
 h:=knowledge.publish(r,ids);
 ELSIF r IS NOT NULL THEN RAISE EXCEPTION 'no active membership' USING ERRCODE='23514'; END IF;
 INSERT INTO knowledge.correction(old_id,new_id,reason,basis,actor) VALUES(old_v,new_v,reason_text,basis_text,actor_text);
 INSERT INTO knowledge.withdrawal(version_id,reason,actor) VALUES(old_v,reason_text,actor_text) ON CONFLICT DO NOTHING;
 UPDATE knowledge.review_task SET resolved_at=clock_timestamp() WHERE version_id=old_v AND resolved_at IS NULL;
 RETURN h;
 END $$;

CREATE FUNCTION knowledge.immutable_row() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
 BEGIN RAISE EXCEPTION 'immutable record' USING ERRCODE='55000'; END $$;
CREATE TRIGGER immutable_claim_version BEFORE UPDATE OR DELETE ON knowledge.claim_version FOR EACH ROW EXECUTE FUNCTION knowledge.immutable_row();
CREATE TRIGGER immutable_release BEFORE UPDATE OR DELETE ON knowledge.release FOR EACH ROW EXECUTE FUNCTION knowledge.immutable_row();
CREATE TRIGGER immutable_member BEFORE UPDATE OR DELETE ON knowledge.release_member FOR EACH ROW EXECUTE FUNCTION knowledge.immutable_row();
CREATE TRIGGER immutable_withdrawal BEFORE UPDATE OR DELETE ON knowledge.withdrawal FOR EACH ROW EXECUTE FUNCTION knowledge.immutable_row();
CREATE TRIGGER immutable_correction BEFORE UPDATE OR DELETE ON knowledge.correction FOR EACH ROW EXECUTE FUNCTION knowledge.immutable_row();

CREATE VIEW public_read.release_claims WITH (security_barrier=true) AS
 SELECT m.release_id,m.version_id,m.payload FROM knowledge.release_member m
 WHERE NOT EXISTS(SELECT 1 FROM knowledge.withdrawal w WHERE w.version_id=m.version_id);
CREATE VIEW public_read.current_claims WITH (security_barrier=true) AS
 SELECT c.* FROM public_read.release_claims c JOIN knowledge.current_release r ON r.release_id=c.release_id;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA knowledge FROM PUBLIC;
GRANT USAGE ON SCHEMA public_read TO satac_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public_read TO satac_reader;
GRANT USAGE ON SCHEMA knowledge TO satac_publisher,satac_curator;
GRANT EXECUTE ON FUNCTION knowledge.publish(uuid,uuid[]),knowledge.correct(uuid,uuid,uuid,text,text,text) TO satac_publisher;
GRANT EXECUTE ON FUNCTION knowledge.flag_incorrect(uuid,text,text) TO satac_curator;
GRANT SELECT ON knowledge.review_task,knowledge.correction,knowledge.withdrawal TO satac_curator;
COMMIT;
