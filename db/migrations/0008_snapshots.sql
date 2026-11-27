BEGIN;
ALTER TABLE knowledge.claim_version DROP CONSTRAINT claim_object_xor;
ALTER TABLE knowledge.claim_version ADD CONSTRAINT claim_object_xor CHECK (
 (predicate IN ('NAME','ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY','ROUTE_SEGMENT','HISTORICAL_SNAPSHOT') AND object_id IS NULL AND object_text IS NOT NULL AND btrim(object_text)<>'' AND language IS NOT NULL AND language IN ('ar','en'))
 OR (predicate NOT IN ('NAME','ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY','ROUTE_SEGMENT','HISTORICAL_SNAPSHOT') AND object_id IS NOT NULL AND object_text IS NULL AND language IS NULL));
INSERT INTO knowledge.predicate VALUES ('HISTORICAL_SNAPSHOT',ARRAY['Work'],ARRAY[]::text[],false);
CREATE FUNCTION knowledge.validate_snapshot(a jsonb) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
 DECLARE r jsonb; k text; g public.geometry; p jsonb;
 BEGIN
 IF jsonb_typeof(a) IS DISTINCT FROM 'object' OR a-ARRAY['type','year','record']<>'{}'::jsonb OR jsonb_typeof(a->'year') IS DISTINCT FROM 'number' OR a->>'year' !~ '^-?[0-9]{1,6}$' OR (a->>'year')::int=0 OR jsonb_typeof(a->'record') IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'invalid snapshot envelope' USING ERRCODE='23514'; END IF;
 r=a->'record';
 IF a->>'type'='territory' THEN
 IF r-ARRAY['id','year','name','source_name','subject','kind','border_precision','geometry','label','source_url','source_blob_sha','browse_url']<>'{}'::jsonb OR r->'year' IS DISTINCT FROM a->'year' OR r->'border_precision' IS DISTINCT FROM '1'::jsonb OR coalesce(r->>'kind','') NOT IN ('polity','region','dependency') THEN RAISE EXCEPTION 'invalid territory fields' USING ERRCODE='23514'; END IF;
 FOREACH k IN ARRAY ARRAY['id','name','source_name','subject','source_url','source_blob_sha','browse_url'] LOOP
 IF jsonb_typeof(r->k) IS DISTINCT FROM 'string' OR btrim(r->>k)='' THEN RAISE EXCEPTION 'invalid territory text' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF r->>'source_blob_sha' !~ '^[0-9a-f]{40}$' OR r->>'source_url' !~ '^https://' OR r->>'browse_url' !~ '^https://' OR coalesce(r->'geometry'->>'type','') NOT IN ('Polygon','MultiPolygon') THEN RAISE EXCEPTION 'invalid territory source/geometry' USING ERRCODE='23514'; END IF;
 g=public.ST_SetSRID(public.ST_GeomFromGeoJSON(r->'geometry'),4326);
 IF g IS NULL OR public.ST_IsEmpty(g) OR NOT public.ST_IsValid(g) OR public.ST_NDims(g)<>2 OR public.ST_Area(g)<=0 OR public.ST_XMin(g)<-180 OR public.ST_XMax(g)>180 OR public.ST_YMin(g)<-90 OR public.ST_YMax(g)>90 THEN RAISE EXCEPTION 'invalid territory polygon' USING ERRCODE='23514'; END IF;
 p=r->'label';
 ELSIF a->>'type'='milestone' THEN
 IF r-ARRAY['title','place','p','article','text']<>'{}'::jsonb THEN RAISE EXCEPTION 'invalid milestone fields' USING ERRCODE='23514'; END IF;
 FOREACH k IN ARRAY ARRAY['title','place','article','text'] LOOP
 IF jsonb_typeof(r->k) IS DISTINCT FROM 'string' OR btrim(r->>k)='' THEN RAISE EXCEPTION 'invalid milestone text' USING ERRCODE='23514'; END IF;
 END LOOP;
 p=r->'p';
 ELSE RAISE EXCEPTION 'invalid snapshot type' USING ERRCODE='23514'; END IF;
 IF jsonb_typeof(p) IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'invalid anchor' USING ERRCODE='23514'; END IF;
 IF jsonb_array_length(p)<>2 OR jsonb_typeof(p->0) IS DISTINCT FROM 'number' OR jsonb_typeof(p->1) IS DISTINCT FROM 'number' THEN RAISE EXCEPTION 'invalid anchor' USING ERRCODE='23514'; END IF;
 IF (p->>0)::numeric NOT BETWEEN -180 AND 180 OR (p->>1)::numeric NOT BETWEEN -90 AND 90 THEN RAISE EXCEPTION 'anchor range' USING ERRCODE='23514'; END IF;
 END $$;
REVOKE ALL ON FUNCTION knowledge.validate_snapshot(jsonb) FROM PUBLIC;
CREATE OR REPLACE FUNCTION knowledge.validate_relation() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,knowledge AS $$
 DECLARE p knowledge.predicate; s text; o text;
 BEGIN
 SELECT * INTO STRICT p FROM knowledge.predicate WHERE code=NEW.predicate;
 SELECT kind INTO STRICT s FROM knowledge.entity WHERE id=NEW.subject_id;
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
 'object_text',CASE WHEN c.predicate NOT IN ('ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY','ROUTE_SEGMENT') THEN c.object_text END,'language',c.language,
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
 )) FROM knowledge.claim_version c WHERE c.id=v $$;







CREATE VIEW public_read.snapshots WITH (security_barrier=true) AS
 SELECT release_id,version_id,payload->'snapshot' AS snapshot,payload->'temporal' AS temporal
 FROM public_read.release_claims WHERE payload->>'predicate'='HISTORICAL_SNAPSHOT';
GRANT SELECT ON public_read.snapshots TO satac_reader;
COMMIT;
