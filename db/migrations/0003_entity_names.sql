BEGIN;
ALTER TABLE knowledge.claim_version ALTER COLUMN object_id DROP NOT NULL;
ALTER TABLE knowledge.claim_version ADD COLUMN object_text text, ADD COLUMN language text;
ALTER TABLE knowledge.claim_version ADD CONSTRAINT claim_object_xor CHECK (
 (predicate='NAME' AND object_id IS NULL AND object_text IS NOT NULL AND btrim(object_text)<>'' AND language IS NOT NULL AND language IN ('ar','en'))
 OR (predicate<>'NAME' AND object_id IS NOT NULL AND object_text IS NULL AND language IS NULL)
);
INSERT INTO knowledge.predicate VALUES ('NAME',ARRAY['*'],ARRAY[]::text[],false);
CREATE OR REPLACE FUNCTION knowledge.validate_relation() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,knowledge AS $$
 DECLARE p knowledge.predicate; s text; o text;
 BEGIN
 SELECT * INTO STRICT p FROM knowledge.predicate WHERE code=NEW.predicate;
 SELECT kind INTO STRICT s FROM knowledge.entity WHERE id=NEW.subject_id;
 IF NEW.predicate='NAME' THEN
 IF NEW.object_id IS NOT NULL OR NEW.object_text IS NULL OR btrim(NEW.object_text)='' OR NEW.language IS NULL OR NEW.language NOT IN ('ar','en') THEN
 RAISE EXCEPTION 'invalid name claim' USING ERRCODE='23514'; END IF;
 RETURN NEW;
 END IF;
 IF NEW.object_id IS NULL OR NEW.object_text IS NOT NULL OR NEW.language IS NOT NULL THEN
 RAISE EXCEPTION 'invalid relation object' USING ERRCODE='23514'; END IF;
 SELECT kind INTO STRICT o FROM knowledge.entity WHERE id=NEW.object_id;
 IF NOT (s=ANY(p.domain_types) OR '*'=ANY(p.domain_types)) OR
    NOT (o=ANY(p.range_types) OR '*'=ANY(p.range_types)) OR
    (p.requires_justification AND nullif(btrim(NEW.justification),'') IS NULL)
 THEN RAISE EXCEPTION 'invalid relation' USING ERRCODE='23514'; END IF;
 RETURN NEW;
 END $$;

CREATE OR REPLACE FUNCTION knowledge.project(v uuid) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog,knowledge,public AS $$
 SELECT jsonb_strip_nulls(jsonb_build_object(
 'claim_id',c.claim_id,'version_id',c.id,'subject_id',c.subject_id,'predicate',c.predicate,'object_id',c.object_id,
 'scientific_note',c.scientific_note,
 'object_text',c.object_text,'language',c.language,
 'entity_kind',CASE WHEN c.predicate='NAME' THEN (SELECT kind FROM knowledge.entity WHERE id=c.subject_id) END,
 'temporal',(SELECT to_jsonb(t)-'version_id' FROM knowledge.temporal_extent t WHERE t.version_id=c.id),
 'geometries',(SELECT jsonb_agg(jsonb_strip_nulls(jsonb_build_object('role',g.role,'geometry',public.ST_AsGeoJSON(g.geom,15)::jsonb,'precision',g.precision_label,'uncertainty_m',g.uncertainty_m)) ORDER BY g.id)
 FROM knowledge.geometry_attestation g WHERE g.version_id=c.id AND NOT g.restricted),
 'references',(SELECT jsonb_agg(jsonb_strip_nulls(jsonb_build_object('source_version_id',s.id,'title',s.title,'locator',e.locator,'stance',e.stance)) ORDER BY e.id)
 FROM knowledge.evidence e JOIN knowledge.source_version s ON s.id=e.source_version_id WHERE e.version_id=c.id AND NOT s.restricted)
 )) FROM knowledge.claim_version c WHERE c.id=v $$;


CREATE FUNCTION public_read.search_key(value text) RETURNS text LANGUAGE sql IMMUTABLE STRICT
 SET search_path=pg_catalog AS $$
 SELECT btrim(regexp_replace(translate(lower(normalize(value,NFKC)), 'أإآٱى', 'ااااي'), '[ًٌٍَُِّْٰـ]', '', 'g')) $$;
REVOKE ALL ON FUNCTION public_read.search_key(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public_read.search_key(text) TO satac_reader;
CREATE TABLE knowledge.legacy_crosswalk (
 namespace text NOT NULL,legacy_id text NOT NULL,entity_id uuid NOT NULL REFERENCES knowledge.entity,
 PRIMARY KEY(namespace,legacy_id),UNIQUE(namespace,entity_id)
);
CREATE VIEW public_read.entity_names WITH (security_barrier=true) AS
 SELECT release_id,version_id,(payload->>'claim_id')::uuid AS claim_id,
 (payload->>'subject_id')::uuid AS entity_id,payload->>'entity_kind' AS kind,
 payload->>'object_text' AS name,payload->>'language' AS lang,payload->'temporal' AS temporal
 FROM public_read.release_claims WHERE payload->>'predicate'='NAME';
GRANT SELECT ON public_read.entity_names TO satac_reader;
COMMIT;
