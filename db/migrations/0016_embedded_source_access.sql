-- A07: explicit owner decisions about embedded structured content.
BEGIN;
CREATE TABLE knowledge.embedded_source_revocation (
 source_version_id uuid PRIMARY KEY REFERENCES knowledge.source_version,
 reason text NOT NULL CHECK(btrim(reason)<>''), actor text NOT NULL CHECK(btrim(actor)<>''),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TRIGGER immutable_embedded_source_revocation BEFORE UPDATE OR DELETE ON knowledge.embedded_source_revocation
 FOR EACH ROW EXECUTE FUNCTION knowledge.immutable_row();

-- Explicit action distinct from ordinary evidence-only source revocation.
-- Withhold entire structured payloads to preserve downstream schema assumptions.
CREATE FUNCTION knowledge.revoke_embedded_source(s uuid,reason_text text,actor_text text) RETURNS void
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,knowledge AS $$
 BEGIN
 PERFORM knowledge.revoke_source(s,reason_text,actor_text);
 INSERT INTO knowledge.embedded_source_revocation(source_version_id,reason,actor) VALUES(s,reason_text,actor_text) ON CONFLICT DO NOTHING;
 END $$;
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
 WHERE NOT EXISTS(SELECT 1 FROM knowledge.withdrawal w WHERE w.version_id=m.version_id)
 AND NOT EXISTS (
   SELECT 1 FROM knowledge.embedded_source_revocation x
   WHERE m.payload->>'predicate' IN ('ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY','ROUTE_SEGMENT','HISTORICAL_SNAPSHOT','GEOLOGY_RECORD','CELL_METRIC','EXTENDED_TOPIC')
     AND m.payload->'references' @> jsonb_build_array(jsonb_build_object('source_version_id',x.source_version_id))
 );

REVOKE ALL ON FUNCTION knowledge.revoke_embedded_source(uuid,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION knowledge.revoke_embedded_source(uuid,text,text) TO satac_curator;
GRANT SELECT ON knowledge.embedded_source_revocation TO satac_curator;
COMMIT;
