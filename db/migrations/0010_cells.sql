BEGIN;
ALTER TABLE knowledge.claim_version DROP CONSTRAINT claim_object_xor;
ALTER TABLE knowledge.claim_version ADD CONSTRAINT claim_object_xor CHECK (
 (predicate IN ('NAME','ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY','ROUTE_SEGMENT','HISTORICAL_SNAPSHOT','GEOLOGY_RECORD','CELL_METRIC') AND object_id IS NULL AND object_text IS NOT NULL AND btrim(object_text)<>'' AND language IS NOT NULL AND language IN ('ar','en'))
 OR (predicate NOT IN ('NAME','ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY','ROUTE_SEGMENT','HISTORICAL_SNAPSHOT','GEOLOGY_RECORD','CELL_METRIC') AND object_id IS NOT NULL AND object_text IS NULL AND language IS NULL));
INSERT INTO knowledge.predicate VALUES ('CELL_METRIC',ARRAY['Place'],ARRAY[]::text[],false);
CREATE FUNCTION knowledge.validate_cell(a jsonb) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
 DECLARE k text; p jsonb; lon double precision; lat double precision;
 BEGIN
 IF jsonb_typeof(a) IS DISTINCT FROM 'object' OR a-ARRAY['id','c','t','area_km2','water_km','radius','province_ids']<>'{}'::jsonb THEN RAISE EXCEPTION 'invalid cell envelope' USING ERRCODE='23514'; END IF;
 FOREACH k IN ARRAY ARRAY['c','t','area_km2','water_km','radius'] LOOP
 IF jsonb_typeof(a->k) IS DISTINCT FROM 'number' THEN RAISE EXCEPTION 'invalid metric type' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF a->>'c' !~ '^[0-9]{1,4}$' OR a->>'t' !~ '^[0-9]{1,4}$' OR a->>'id' IS DISTINCT FROM ((a->>'c')||','||(a->>'t')) OR a->'radius' IS DISTINCT FROM '0.72'::jsonb OR (a->>'area_km2')::numeric<=0 OR (a->>'water_km')::numeric<0 THEN RAISE EXCEPTION 'invalid grid or metric' USING ERRCODE='23514'; END IF;
 lon=(a->>'c')::int*1.5*0.72*0.36-180;
 lat=90-((a->>'t')::int+((a->>'c')::int%2)*0.5)*sqrt(3.0)*0.72*0.36;
 IF lon NOT BETWEEN 34 AND 60 OR lat NOT BETWEEN 12 AND 34 THEN RAISE EXCEPTION 'cell center outside source coverage' USING ERRCODE='23514'; END IF;
 IF jsonb_typeof(a->'province_ids') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'invalid province list' USING ERRCODE='23514'; END IF;
 FOR p IN SELECT value FROM jsonb_array_elements(a->'province_ids') LOOP
 IF jsonb_typeof(p)<>'number' OR p#>>'{}' !~ '^[1-9][0-9]{0,8}$' THEN RAISE EXCEPTION 'invalid province ID' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF (SELECT count(DISTINCT value) FROM jsonb_array_elements(a->'province_ids'))<>jsonb_array_length(a->'province_ids') THEN RAISE EXCEPTION 'duplicate province' USING ERRCODE='23514'; END IF;
 END $$;
REVOKE ALL ON FUNCTION knowledge.validate_cell(jsonb) FROM PUBLIC;
CREATE OR REPLACE FUNCTION knowledge.validate_relation() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,knowledge AS $$
 DECLARE p knowledge.predicate; s text; o text;
 BEGIN
 SELECT * INTO STRICT p FROM knowledge.predicate WHERE code=NEW.predicate;
 SELECT kind INTO STRICT s FROM knowledge.entity WHERE id=NEW.subject_id;
 IF NEW.predicate='CELL_METRIC' THEN
 IF s<>'Place' OR NEW.object_id IS NOT NULL OR NEW.object_text IS NULL OR NEW.language IS DISTINCT FROM 'ar' THEN RAISE EXCEPTION 'invalid cell metric' USING ERRCODE='23514'; END IF;
 PERFORM knowledge.validate_cell(NEW.object_text::jsonb);
 RETURN NEW;
 END IF;
 IF NEW.predicate='GEOLOGY_RECORD' THEN
 IF s<>'Place' OR NEW.object_id IS NOT NULL OR NEW.object_text IS NULL OR NEW.language IS DISTINCT FROM 'ar' THEN RAISE EXCEPTION 'invalid geology record' USING ERRCODE='23514'; END IF;
 PERFORM knowledge.validate_geology(NEW.object_text::jsonb);
 RETURN NEW;
 END IF;
 IF NEW.predicate='HISTORICAL_SNAPSHOT' THEN
 IF s<>'Work' OR NEW.object_id IS NOT NULL OR NEW.object_text IS NULL OR NEW.language IS DISTINCT FROM 'ar' THEN RAISE EXCEPTION 'invalid historical snapshot' USING ERRCODE='23514'; END IF;
 PERFORM knowledge.validate_snapshot(NEW.object_text::jsonb);
 RETURN NEW;
 END IF;
 IF NEW.predicate='ROUTE_SEGMENT' THEN
 IF s<>'Route' OR NEW.object_id IS NOT NULL OR NEW.object_text IS NULL OR NEW.language IS DISTINCT FROM 'ar' THEN RAISE EXCEPTION 'invalid route segment' USING ERRCODE='23514'; END IF;
 PERFORM knowledge.validate_route(NEW.object_text::jsonb);
 RETURN NEW;
 END IF;
 IF NEW.predicate='DIRECTORY_ENTRY' THEN
 IF s<>'Place' OR NEW.object_id IS NOT NULL OR NEW.object_text IS NULL OR NEW.language IS DISTINCT FROM 'ar' THEN RAISE EXCEPTION 'invalid directory entry' USING ERRCODE='23514'; END IF;
 PERFORM knowledge.validate_directory(NEW.object_text::jsonb);
 RETURN NEW;
 END IF;
 IF NEW.predicate IN ('EDITORIAL_LINK','EDITORIAL_JOURNEY') THEN
 IF s<>'Work' OR NEW.object_id IS NOT NULL OR NEW.object_text IS NULL OR NEW.language IS DISTINCT FROM 'ar' THEN RAISE EXCEPTION 'invalid editorial record' USING ERRCODE='23514'; END IF;
 PERFORM knowledge.validate_editorial(NEW.predicate,NEW.object_text::jsonb);
 RETURN NEW;
 END IF;
 IF NEW.predicate='ARTICLE' THEN
 IF s<>'Work' OR NEW.object_id IS NOT NULL OR NEW.object_text IS NULL OR NEW.language IS DISTINCT FROM 'ar' THEN
 RAISE EXCEPTION 'invalid article claim' USING ERRCODE='23514'; END IF;
 PERFORM knowledge.validate_article(NEW.object_text::jsonb);
 RETURN NEW;
 END IF;
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
 'object_text',CASE WHEN c.predicate NOT IN ('ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY','ROUTE_SEGMENT','HISTORICAL_SNAPSHOT','GEOLOGY_RECORD','CELL_METRIC') THEN c.object_text END,'language',c.language,
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
 )) || CASE WHEN c.predicate='GEOLOGY_RECORD' THEN jsonb_build_object('geology',c.object_text::jsonb) ELSE '{}'::jsonb END || CASE WHEN c.predicate='CELL_METRIC' THEN jsonb_build_object('cell',c.object_text::jsonb) ELSE '{}'::jsonb END FROM knowledge.claim_version c WHERE c.id=v $$;









CREATE VIEW public_read.cells WITH (security_barrier=true) AS SELECT release_id,version_id,payload->'cell' AS cell FROM public_read.release_claims WHERE payload->>'predicate'='CELL_METRIC';
GRANT SELECT ON public_read.cells TO satac_reader;
COMMIT;
