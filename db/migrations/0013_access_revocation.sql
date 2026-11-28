-- Append-only access decisions; original release manifests remain immutable.
BEGIN;
CREATE TABLE knowledge.source_revocation (
 source_version_id uuid PRIMARY KEY REFERENCES knowledge.source_version,
 reason text NOT NULL CHECK(btrim(reason)<>''), actor text NOT NULL CHECK(btrim(actor)<>''),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE knowledge.geometry_revocation (
 version_id uuid NOT NULL REFERENCES knowledge.claim_version,
 geometry_sha256 text NOT NULL CHECK(geometry_sha256 ~ '^[0-9a-f]{64}$'),
 origin_release_id uuid NOT NULL REFERENCES knowledge.release,
 reason text NOT NULL CHECK(btrim(reason)<>''), actor text NOT NULL CHECK(btrim(actor)<>''),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(version_id,geometry_sha256)
);
CREATE TRIGGER immutable_source_revocation BEFORE UPDATE OR DELETE ON knowledge.source_revocation FOR EACH ROW EXECUTE FUNCTION knowledge.immutable_row();
CREATE TRIGGER immutable_geometry_revocation BEFORE UPDATE OR DELETE ON knowledge.geometry_revocation FOR EACH ROW EXECUTE FUNCTION knowledge.immutable_row();

CREATE FUNCTION knowledge.revoke_source(s uuid,reason_text text,actor_text text) RETURNS void
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,knowledge AS $$
 BEGIN
 PERFORM pg_advisory_xact_lock(716032);
 IF s IS NULL OR NOT EXISTS(SELECT 1 FROM knowledge.source_version WHERE id=s)
 OR nullif(btrim(reason_text),'') IS NULL OR nullif(btrim(actor_text),'') IS NULL THEN
 RAISE EXCEPTION 'invalid source revocation' USING ERRCODE='23514'; END IF;
 INSERT INTO knowledge.source_revocation(source_version_id,reason,actor) VALUES(s,reason_text,actor_text) ON CONFLICT DO NOTHING;
 END $$;

-- The curator selects a one-based index in the PRIVATE stored release geometry array.
-- Match the exact GeoJSON geometry independently of role/precision metadata, within version_id.
CREATE FUNCTION knowledge.revoke_geometry(r uuid,v uuid,ordinal integer,reason_text text,actor_text text) RETURNS void
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,knowledge,public AS $$
 DECLARE g jsonb;
 BEGIN
 PERFORM pg_advisory_xact_lock(716032);
 IF ordinal IS NULL OR ordinal<1 OR nullif(btrim(reason_text),'') IS NULL OR nullif(btrim(actor_text),'') IS NULL THEN
 RAISE EXCEPTION 'invalid geometry revocation' USING ERRCODE='23514'; END IF;
 SELECT m.payload->'geometries'->(ordinal-1)->'geometry' INTO g FROM knowledge.release_member m
 WHERE m.release_id=r AND m.version_id=v;
 IF g IS NULL OR jsonb_typeof(g) IS DISTINCT FROM 'object' THEN
 RAISE EXCEPTION 'stored geometry not found' USING ERRCODE='23514'; END IF;
 INSERT INTO knowledge.geometry_revocation(version_id,geometry_sha256,origin_release_id,reason,actor)
 VALUES(v,encode(public.digest(convert_to(g::text,'UTF8'),'sha256'),'hex'),r,reason_text,actor_text)
 ON CONFLICT DO NOTHING;
 END $$;

-- Embedded legacy literals (articles, route lines, directory locations, etc.) are not
-- generic attestations. Withhold the whole version when selective masking is unsafe.
-- Access withholding is not an assertion of factual error and creates no correction task.
CREATE FUNCTION knowledge.withhold_version(v uuid,reason_text text,actor_text text) RETURNS void
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,knowledge AS $$
 BEGIN
 PERFORM pg_advisory_xact_lock(716032);
 IF v IS NULL OR NOT EXISTS(SELECT 1 FROM knowledge.claim_version WHERE id=v)
 OR nullif(btrim(reason_text),'') IS NULL OR nullif(btrim(actor_text),'') IS NULL THEN
 RAISE EXCEPTION 'invalid access withholding' USING ERRCODE='23514'; END IF;
 INSERT INTO knowledge.withdrawal(version_id,reason,actor) VALUES(v,reason_text,actor_text) ON CONFLICT DO NOTHING;
 END $$;

-- One common public projection for claims, relation graph, search and derived views.
-- Do not expose decisions, identities of curators, or audit reasons.
CREATE OR REPLACE VIEW public_read.release_claims WITH (security_barrier=true) AS
 SELECT m.release_id,m.version_id,
 (m.payload-'references'-'geometries')
 || CASE WHEN refs.kept IS NULL THEN '{}'::jsonb ELSE jsonb_build_object('references',refs.kept) END
 || CASE WHEN geoms.kept IS NULL THEN '{}'::jsonb ELSE jsonb_build_object('geometries',geoms.kept) END AS payload
 FROM knowledge.release_member m
 LEFT JOIN LATERAL (
 SELECT jsonb_agg(e ORDER BY ord) AS kept
 FROM jsonb_array_elements(coalesce(m.payload->'references','[]'::jsonb)) WITH ORDINALITY AS a(e,ord)
 WHERE EXISTS(SELECT 1 FROM knowledge.source_version s WHERE s.id=(e->>'source_version_id')::uuid AND NOT s.restricted
 AND NOT EXISTS(SELECT 1 FROM knowledge.source_revocation sr WHERE sr.source_version_id=s.id))
 ) refs ON true
 LEFT JOIN LATERAL (
 SELECT jsonb_agg(g ORDER BY ord) AS kept
 FROM jsonb_array_elements(coalesce(m.payload->'geometries','[]'::jsonb)) WITH ORDINALITY AS a(g,ord)
 WHERE NOT EXISTS(SELECT 1 FROM knowledge.geometry_revocation gr WHERE gr.version_id=m.version_id
 AND gr.geometry_sha256=encode(public.digest(convert_to((g->'geometry')::text,'UTF8'),'sha256'),'hex'))
 ) geoms ON true
 WHERE NOT EXISTS(SELECT 1 FROM knowledge.withdrawal w WHERE w.version_id=m.version_id);
REVOKE ALL ON FUNCTION knowledge.revoke_source(uuid,text,text),knowledge.revoke_geometry(uuid,uuid,integer,text,text),knowledge.withhold_version(uuid,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION knowledge.revoke_source(uuid,text,text),knowledge.revoke_geometry(uuid,uuid,integer,text,text),knowledge.withhold_version(uuid,text,text) TO satac_curator;
GRANT SELECT ON knowledge.source_revocation,knowledge.geometry_revocation TO satac_curator;
COMMIT;
