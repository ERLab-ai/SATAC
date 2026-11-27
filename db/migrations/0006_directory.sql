BEGIN;
ALTER TABLE knowledge.claim_version DROP CONSTRAINT claim_object_xor;
ALTER TABLE knowledge.claim_version ADD CONSTRAINT claim_object_xor CHECK (
 (predicate IN ('NAME','ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY') AND object_id IS NULL AND object_text IS NOT NULL AND btrim(object_text)<>'' AND language IS NOT NULL AND language IN ('ar','en'))
 OR (predicate NOT IN ('NAME','ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY') AND object_id IS NOT NULL AND object_text IS NULL AND language IS NULL));
INSERT INTO knowledge.predicate VALUES ('DIRECTORY_ENTRY',ARRAY['Place'],ARRAY[]::text[],false);
CREATE FUNCTION knowledge.validate_directory(a jsonb) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
 DECLARE r jsonb; k text;
 BEGIN
 IF jsonb_typeof(a) IS DISTINCT FROM 'object' OR a-ARRAY['collection','region_label','record']<>'{}'::jsonb OR a->>'collection' IS NULL OR a->>'collection' NOT IN ('historical','modern') OR jsonb_typeof(a->'region_label') IS DISTINCT FROM 'string' OR btrim(a->>'region_label')='' OR jsonb_typeof(a->'record') IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'invalid directory envelope' USING ERRCODE='23514'; END IF;
 r=a->'record';
 IF jsonb_typeof(r->'name') IS DISTINCT FROM 'string' OR btrim(r->>'name')='' OR jsonb_typeof(r->'lon') IS DISTINCT FROM 'number' OR jsonb_typeof(r->'lat') IS DISTINCT FROM 'number' THEN RAISE EXCEPTION 'invalid directory name or coordinates' USING ERRCODE='23514'; END IF;
 IF (r->>'lon')::numeric NOT BETWEEN -180 AND 180 OR (r->>'lat')::numeric NOT BETWEEN -90 AND 90 THEN RAISE EXCEPTION 'invalid directory coordinate range' USING ERRCODE='23514'; END IF;
 IF a->>'collection'='historical' THEN
 IF r-ARRAY['id','name','lon','lat','region','kind','source_certainty','source_uri','source_url','source_blob_sha']<>'{}'::jsonb THEN RAISE EXCEPTION 'invalid historical keys' USING ERRCODE='23514'; END IF;
 FOREACH k IN ARRAY ARRAY['id','region','kind','source_certainty'] LOOP
 IF jsonb_typeof(r->k) IS DISTINCT FROM 'string' OR btrim(r->>k)='' THEN RAISE EXCEPTION 'invalid historical field' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF r->>'kind' NOT IN ('towns','waystations','villages','regions','sites','metropoles','waters','capitals') OR r->>'source_certainty' NOT IN ('certain','not_stated') OR r->>'region'<>a->>'region_label' THEN RAISE EXCEPTION 'invalid historical classification' USING ERRCODE='23514'; END IF;
 FOREACH k IN ARRAY ARRAY['source_uri','source_url','source_blob_sha'] LOOP
 IF r ? k AND jsonb_typeof(r->k) IS DISTINCT FROM 'string' THEN RAISE EXCEPTION 'invalid source field' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF r ? 'source_url' AND r->>'source_url' !~ '^https://' THEN RAISE EXCEPTION 'invalid source URL' USING ERRCODE='23514'; END IF;
 ELSE
 IF r-ARRAY['id','region','name','en','lon','lat','rank']<>'{}'::jsonb OR jsonb_typeof(r->'en') IS DISTINCT FROM 'string' OR btrim(r->>'en')='' THEN RAISE EXCEPTION 'invalid modern keys' USING ERRCODE='23514'; END IF;
 FOREACH k IN ARRAY ARRAY['id','region','rank'] LOOP
 IF jsonb_typeof(r->k) IS DISTINCT FROM 'number' OR r->>k !~ '^[0-9]+$' THEN RAISE EXCEPTION 'invalid modern integer' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF (r->>'region')::int NOT BETWEEN 1 AND 13 OR (r->>'rank')::int NOT BETWEEN 0 AND 2 THEN RAISE EXCEPTION 'invalid modern classification' USING ERRCODE='23514'; END IF;
 END IF;
 END $$;
REVOKE ALL ON FUNCTION knowledge.validate_directory(jsonb) FROM PUBLIC;
CREATE OR REPLACE FUNCTION knowledge.validate_relation() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,knowledge AS $$
 DECLARE p knowledge.predicate; s text; o text;
 BEGIN
 SELECT * INTO STRICT p FROM knowledge.predicate WHERE code=NEW.predicate;
 SELECT kind INTO STRICT s FROM knowledge.entity WHERE id=NEW.subject_id;
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
 'object_text',CASE WHEN c.predicate NOT IN ('ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY') THEN c.object_text END,'language',c.language,
 'article',CASE WHEN c.predicate='ARTICLE' THEN c.object_text::jsonb END,
 'directory',CASE WHEN c.predicate='DIRECTORY_ENTRY' THEN c.object_text::jsonb END,
 'editorial',CASE WHEN c.predicate IN ('EDITORIAL_LINK','EDITORIAL_JOURNEY') THEN c.object_text::jsonb END,
 'entity_kind',CASE WHEN c.predicate='NAME' THEN (SELECT kind FROM knowledge.entity WHERE id=c.subject_id) END,
 'temporal',(SELECT to_jsonb(t)-'version_id' FROM knowledge.temporal_extent t WHERE t.version_id=c.id),
 'geometries',(SELECT jsonb_agg(jsonb_strip_nulls(jsonb_build_object('role',g.role,'geometry',public.ST_AsGeoJSON(g.geom,15)::jsonb,'precision',g.precision_label,'uncertainty_m',g.uncertainty_m)) ORDER BY g.id)
 FROM knowledge.geometry_attestation g WHERE g.version_id=c.id AND NOT g.restricted),
 'references',(SELECT jsonb_agg(jsonb_strip_nulls(jsonb_build_object('source_version_id',s.id,'title',s.title,'locator',e.locator,'stance',e.stance)) ORDER BY e.id)
 FROM knowledge.evidence e JOIN knowledge.source_version s ON s.id=e.source_version_id WHERE e.version_id=c.id AND NOT s.restricted)
 )) FROM knowledge.claim_version c WHERE c.id=v $$;





CREATE VIEW public_read.directory WITH (security_barrier=true) AS
 SELECT release_id,version_id,(payload->>'subject_id')::uuid AS entity_id,payload->'directory' AS directory,
 coalesce(payload->'references','[]'::jsonb) AS references
 FROM public_read.release_claims WHERE payload->>'predicate'='DIRECTORY_ENTRY';
GRANT SELECT ON public_read.directory TO satac_reader;
COMMIT;
