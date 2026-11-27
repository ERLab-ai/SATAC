-- A05: explicit scientific conflict groups, immutable version-scoped membership.
BEGIN;
CREATE TABLE knowledge.scientific_conflict_group (
 id uuid PRIMARY KEY,
 subject_id uuid NOT NULL REFERENCES knowledge.entity,
 predicate text NOT NULL REFERENCES knowledge.predicate,
 UNIQUE(id,subject_id,predicate),
 CHECK(predicate NOT IN ('ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY','ROUTE_SEGMENT','HISTORICAL_SNAPSHOT','GEOLOGY_RECORD','CELL_METRIC','EXTENDED_TOPIC'))
);
CREATE TRIGGER immutable_conflict_group BEFORE UPDATE OR DELETE ON knowledge.scientific_conflict_group
 FOR EACH ROW EXECUTE FUNCTION knowledge.immutable_row();
ALTER TABLE knowledge.claim_version ADD COLUMN conflict_group_id uuid;
ALTER TABLE knowledge.claim_version ADD CONSTRAINT scientific_conflict_scope
 FOREIGN KEY(conflict_group_id,subject_id,predicate)
 REFERENCES knowledge.scientific_conflict_group(id,subject_id,predicate);
-- Existing immutable claim-version trigger also protects conflict assignment.
-- Old release payloads remain unchanged; only newly projected versions gain this field.
CREATE OR REPLACE FUNCTION knowledge.project(v uuid) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog,knowledge,public AS $$
 SELECT jsonb_strip_nulls(jsonb_build_object(
 'claim_id',c.claim_id,'version_id',c.id,'subject_id',c.subject_id,'predicate',c.predicate,'object_id',c.object_id,
 'scientific_note',c.scientific_note,'conflict_group_id',c.conflict_group_id,
 'object_text',CASE WHEN c.predicate NOT IN ('ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY','ROUTE_SEGMENT','HISTORICAL_SNAPSHOT','GEOLOGY_RECORD','CELL_METRIC','EXTENDED_TOPIC') THEN c.object_text END,'language',c.language,
 'article',CASE WHEN c.predicate='ARTICLE' THEN c.object_text::jsonb END,
 'directory',CASE WHEN c.predicate='DIRECTORY_ENTRY' THEN c.object_text::jsonb END,
 'route_segment',CASE WHEN c.predicate='ROUTE_SEGMENT' THEN c.object_text::jsonb END,
 'snapshot',CASE WHEN c.predicate='HISTORICAL_SNAPSHOT' THEN c.object_text::jsonb END,
 'editorial',CASE WHEN c.predicate IN ('EDITORIAL_LINK','EDITORIAL_JOURNEY') THEN c.object_text::jsonb END,
 'entity_kind',CASE WHEN c.predicate='NAME' THEN (SELECT kind FROM knowledge.entity WHERE id=c.subject_id) END,
 'temporal',(SELECT to_jsonb(t)-'version_id' FROM knowledge.temporal_extent t WHERE t.version_id=c.id),
 'geometries',(SELECT jsonb_agg(jsonb_strip_nulls(jsonb_build_object('role',g.role,'geometry',public.ST_AsGeoJSON(g.geom,15)::jsonb,'precision',g.precision_label,'uncertainty_m',g.uncertainty_m)) ORDER BY g.id)
 FROM knowledge.geometry_attestation g WHERE g.version_id=c.id AND NOT g.restricted),
 'references',(SELECT jsonb_agg(jsonb_strip_nulls(jsonb_build_object('source_version_id',s.id,'title',s.title,'locator',e.locator,'stance',e.stance)) ORDER BY e.id)
 FROM knowledge.evidence e JOIN knowledge.source_version s ON s.id=e.source_version_id WHERE e.version_id=c.id AND NOT s.restricted)
 )) || CASE WHEN c.predicate='GEOLOGY_RECORD' THEN jsonb_build_object('geology',c.object_text::jsonb) ELSE '{}'::jsonb END || CASE WHEN c.predicate='CELL_METRIC' THEN jsonb_build_object('cell',c.object_text::jsonb) ELSE '{}'::jsonb END || CASE WHEN c.predicate='EXTENDED_TOPIC' THEN jsonb_build_object('topic',c.object_text::jsonb) ELSE '{}'::jsonb END FROM knowledge.claim_version c WHERE c.id=v $$;
-- No grants to reader on knowledge tables; public API reads existing masked snapshots only.
REVOKE ALL ON knowledge.scientific_conflict_group FROM PUBLIC;
COMMIT;
