-- Editorial works are versioned publication members, not individual historical facts.
BEGIN;
ALTER TABLE knowledge.claim_version DROP CONSTRAINT claim_object_xor;
ALTER TABLE knowledge.claim_version ADD CONSTRAINT claim_object_xor CHECK (
 (predicate IN ('NAME','ARTICLE') AND object_id IS NULL AND object_text IS NOT NULL AND btrim(object_text)<>'' AND language IS NOT NULL AND language IN ('ar','en'))
 OR (predicate NOT IN ('NAME','ARTICLE') AND object_id IS NOT NULL AND object_text IS NULL AND language IS NULL));
INSERT INTO knowledge.predicate VALUES ('ARTICLE',ARRAY['Work'],ARRAY[]::text[],false);
CREATE FUNCTION knowledge.validate_article(a jsonb) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
 DECLARE k text; x jsonb;
 BEGIN
 IF jsonb_typeof(a) IS DISTINCT FROM 'object' OR
    a - ARRAY['id','title','subtitle','eras','category','art','location','summary','sections','sources','related','keywords','short_name','heritage_status','bibliography'] <> '{}'::jsonb
 THEN RAISE EXCEPTION 'invalid article keys' USING ERRCODE='23514'; END IF;
 FOREACH k IN ARRAY ARRAY['id','title','subtitle','category','art','summary','keywords'] LOOP
 IF jsonb_typeof(a->k) IS DISTINCT FROM 'string' OR btrim(a->>k)='' THEN RAISE EXCEPTION 'invalid article text' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF a->>'id' !~ '^[a-z0-9_]+$' OR a->>'art' NOT IN ('rock','oasis','tomb','route','port','fort','globe','dam','terrace','dune','industry') THEN RAISE EXCEPTION 'invalid article ID/art' USING ERRCODE='23514'; END IF;
 FOREACH k IN ARRAY ARRAY['short_name','heritage_status'] LOOP
 IF a ? k AND jsonb_typeof(a->k) IS DISTINCT FROM 'string' THEN RAISE EXCEPTION 'invalid optional article field' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOREACH k IN ARRAY ARRAY['eras','sources','related','sections','location','bibliography'] LOOP
 IF jsonb_typeof(a->k) IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'invalid article array' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF jsonb_array_length(a->'location')<>2 OR jsonb_typeof(a->'location'->0)<>'number' OR jsonb_typeof(a->'location'->1)<>'number'
 THEN RAISE EXCEPTION 'invalid article anchor' USING ERRCODE='23514'; END IF;
 IF (a->'location'->>0)::numeric NOT BETWEEN -180 AND 180 OR (a->'location'->>1)::numeric NOT BETWEEN -90 AND 90 THEN RAISE EXCEPTION 'anchor range' USING ERRCODE='23514'; END IF;
 FOR x IN SELECT value FROM jsonb_array_elements(a->'eras') LOOP
 IF jsonb_typeof(x)<>'string' OR x#>>'{}' NOT IN ('deep','ancient','islamic','states','modern') THEN RAISE EXCEPTION 'invalid era tag' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOREACH k IN ARRAY ARRAY['sources','related'] LOOP
 FOR x IN SELECT value FROM jsonb_array_elements(a->k) LOOP
 IF jsonb_typeof(x)<>'string' OR x#>>'{}' !~ '^[a-z0-9_]+$' THEN RAISE EXCEPTION 'invalid article reference ID' USING ERRCODE='23514'; END IF;
 END LOOP;
 END LOOP;
 FOR x IN SELECT value FROM jsonb_array_elements(a->'sections') LOOP
 IF jsonb_typeof(x)<>'object' OR x-ARRAY['title','text']<>'{}'::jsonb OR jsonb_typeof(x->'title') IS DISTINCT FROM 'string' OR jsonb_typeof(x->'text') IS DISTINCT FROM 'string' THEN RAISE EXCEPTION 'invalid section' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR x IN SELECT value FROM jsonb_array_elements(a->'bibliography') LOOP
 IF jsonb_typeof(x)<>'object' OR x-ARRAY['id','title','url']<>'{}'::jsonb OR jsonb_typeof(x->'id') IS DISTINCT FROM 'string' OR jsonb_typeof(x->'title') IS DISTINCT FROM 'string' OR jsonb_typeof(x->'url') IS DISTINCT FROM 'string' OR x->>'url' !~ '^https://' THEN RAISE EXCEPTION 'invalid bibliography' USING ERRCODE='23514'; END IF;
 END LOOP;
 END $$;
REVOKE ALL ON FUNCTION knowledge.validate_article(jsonb) FROM PUBLIC;
CREATE OR REPLACE FUNCTION knowledge.validate_relation() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,knowledge AS $$
 DECLARE p knowledge.predicate; s text; o text;
 BEGIN
 SELECT * INTO STRICT p FROM knowledge.predicate WHERE code=NEW.predicate;
 SELECT kind INTO STRICT s FROM knowledge.entity WHERE id=NEW.subject_id;
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
 'object_text',CASE WHEN c.predicate<>'ARTICLE' THEN c.object_text END,'language',c.language,
 'article',CASE WHEN c.predicate='ARTICLE' THEN c.object_text::jsonb END,
 'entity_kind',CASE WHEN c.predicate='NAME' THEN (SELECT kind FROM knowledge.entity WHERE id=c.subject_id) END,
 'temporal',(SELECT to_jsonb(t)-'version_id' FROM knowledge.temporal_extent t WHERE t.version_id=c.id),
 'geometries',(SELECT jsonb_agg(jsonb_strip_nulls(jsonb_build_object('role',g.role,'geometry',public.ST_AsGeoJSON(g.geom,15)::jsonb,'precision',g.precision_label,'uncertainty_m',g.uncertainty_m)) ORDER BY g.id)
 FROM knowledge.geometry_attestation g WHERE g.version_id=c.id AND NOT g.restricted),
 'references',(SELECT jsonb_agg(jsonb_strip_nulls(jsonb_build_object('source_version_id',s.id,'title',s.title,'locator',e.locator,'stance',e.stance)) ORDER BY e.id)
 FROM knowledge.evidence e JOIN knowledge.source_version s ON s.id=e.source_version_id WHERE e.version_id=c.id AND NOT s.restricted)
 )) FROM knowledge.claim_version c WHERE c.id=v $$;



CREATE VIEW public_read.articles WITH (security_barrier=true) AS
 SELECT release_id,version_id,(payload->>'claim_id')::uuid AS claim_id,(payload->>'subject_id')::uuid AS work_id,
 payload->'article' AS article FROM public_read.release_claims WHERE payload->>'predicate'='ARTICLE' AND payload ? 'article';
GRANT SELECT ON public_read.articles TO satac_reader;
COMMIT;
