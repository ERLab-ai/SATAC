BEGIN;
ALTER TABLE knowledge.claim_version DROP CONSTRAINT claim_object_xor;
ALTER TABLE knowledge.claim_version ADD CONSTRAINT claim_object_xor CHECK (
 (predicate IN ('NAME','ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY','ROUTE_SEGMENT','HISTORICAL_SNAPSHOT','GEOLOGY_RECORD') AND object_id IS NULL AND object_text IS NOT NULL AND btrim(object_text)<>'' AND language IS NOT NULL AND language IN ('ar','en'))
 OR (predicate NOT IN ('NAME','ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY','ROUTE_SEGMENT','HISTORICAL_SNAPSHOT','GEOLOGY_RECORD') AND object_id IS NOT NULL AND object_text IS NULL AND language IS NULL));
INSERT INTO knowledge.predicate VALUES ('GEOLOGY_RECORD',ARRAY['Place'],ARRAY[]::text[],false);
CREATE FUNCTION knowledge.validate_geology(a jsonb) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
 DECLARE r jsonb; k text; g public.geometry; p jsonb;
 BEGIN
 IF jsonb_typeof(a) IS DISTINCT FROM 'object' OR a-ARRAY['type','record','reference','simplification_deg']<>'{}'::jsonb OR jsonb_typeof(a->'record') IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'invalid geology envelope' USING ERRCODE='23514'; END IF;
 r=a->'record';
 FOREACH k IN ARRAY ARRAY['name','en'] LOOP
 IF jsonb_typeof(r->k) IS DISTINCT FROM 'string' OR btrim(r->>k)='' THEN RAISE EXCEPTION 'invalid geology name' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF a->>'type'='province' THEN
 IF r-ARRAY['id','name','en','ring','kind','anchor']<>'{}'::jsonb OR jsonb_typeof(r->'id') IS DISTINCT FROM 'number' OR r->>'id' !~ '^[1-9][0-9]{0,8}$' OR coalesce(r->>'kind','') NOT IN ('shield','basin','volcanic','structure','other') OR jsonb_typeof(r->'ring') IS DISTINCT FROM 'array' OR a->'simplification_deg' IS DISTINCT FROM '0.5'::jsonb OR coalesce(a->>'reference','') !~ '^https://' THEN RAISE EXCEPTION 'invalid province fields' USING ERRCODE='23514'; END IF;
 IF jsonb_array_length(r->'ring')<4 OR jsonb_array_length(r->'ring')>10000 THEN RAISE EXCEPTION 'invalid ring' USING ERRCODE='23514'; END IF;
 FOR p IN SELECT value FROM jsonb_array_elements(r->'ring') LOOP
 PERFORM knowledge.validate_geology_point(p);
 END LOOP;
 g=public.ST_SetSRID(public.ST_GeomFromGeoJSON(jsonb_build_object('type','Polygon','coordinates',jsonb_build_array(r->'ring'))),4326);
 IF g IS NULL OR public.ST_IsEmpty(g) OR NOT public.ST_IsValid(g) OR public.ST_NDims(g)<>2 OR public.ST_Area(g)<=0 THEN RAISE EXCEPTION 'invalid geology polygon' USING ERRCODE='23514'; END IF;
 p=r->'anchor'; PERFORM knowledge.validate_geology_point(p);
 IF NOT public.ST_Covers(g,public.ST_SetSRID(public.ST_MakePoint((p->>0)::double precision,(p->>1)::double precision),4326)) THEN RAISE EXCEPTION 'invalid province anchor' USING ERRCODE='23514'; END IF;
 ELSIF a->>'type'='volcano' THEN
 IF a ? 'reference' OR a ? 'simplification_deg' OR r-ARRAY['id','name','en','lat','lon','elevation','period','last','summary','source']<>'{}'::jsonb OR jsonb_typeof(r->'id') IS DISTINCT FROM 'string' OR r->>'id' !~ '^[0-9]{6}$' OR coalesce(r->>'period','') NOT IN ('holocene','pleistocene') OR coalesce(r->>'source','') <> 'https://volcano.si.edu/volcano.cfm?vn='||(r->>'id') OR coalesce(jsonb_typeof(r->'elevation'),'missing') NOT IN ('number','null') THEN RAISE EXCEPTION 'invalid volcano fields' USING ERRCODE='23514'; END IF;
 FOREACH k IN ARRAY ARRAY['last','summary'] LOOP
 IF jsonb_typeof(r->k) IS DISTINCT FROM 'string' OR btrim(r->>k)='' THEN RAISE EXCEPTION 'invalid volcano text' USING ERRCODE='23514'; END IF;
 END LOOP;
 PERFORM knowledge.validate_geology_point(jsonb_build_array(r->'lon',r->'lat'));
 ELSE RAISE EXCEPTION 'invalid geology type' USING ERRCODE='23514'; END IF;
 END $$;
CREATE FUNCTION knowledge.validate_geology_point(p jsonb) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
 BEGIN
 IF jsonb_typeof(p) IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'invalid point' USING ERRCODE='23514'; END IF;
 IF jsonb_array_length(p)<>2 OR jsonb_typeof(p->0) IS DISTINCT FROM 'number' OR jsonb_typeof(p->1) IS DISTINCT FROM 'number' THEN RAISE EXCEPTION 'invalid coordinate' USING ERRCODE='23514'; END IF;
 IF (p->>0)::numeric NOT BETWEEN -180 AND 180 OR (p->>1)::numeric NOT BETWEEN -90 AND 90 THEN RAISE EXCEPTION 'coordinate range' USING ERRCODE='23514'; END IF;
 END $$;
REVOKE ALL ON FUNCTION knowledge.validate_geology(jsonb),knowledge.validate_geology_point(jsonb) FROM PUBLIC;
CREATE OR REPLACE FUNCTION knowledge.validate_relation() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,knowledge AS $$
 DECLARE p knowledge.predicate; s text; o text;
 BEGIN
 SELECT * INTO STRICT p FROM knowledge.predicate WHERE code=NEW.predicate;
 SELECT kind INTO STRICT s FROM knowledge.entity WHERE id=NEW.subject_id;
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
 'object_text',CASE WHEN c.predicate NOT IN ('ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY','ROUTE_SEGMENT','HISTORICAL_SNAPSHOT','GEOLOGY_RECORD') THEN c.object_text END,'language',c.language,
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
 )) || CASE WHEN c.predicate='GEOLOGY_RECORD' THEN jsonb_build_object('geology',c.object_text::jsonb) ELSE '{}'::jsonb END FROM knowledge.claim_version c WHERE c.id=v $$;








CREATE VIEW public_read.geology WITH (security_barrier=true) AS
 SELECT release_id,version_id,payload->'geology' AS geology FROM public_read.release_claims WHERE payload->>'predicate'='GEOLOGY_RECORD';
GRANT SELECT ON public_read.geology TO satac_reader;
COMMIT;
