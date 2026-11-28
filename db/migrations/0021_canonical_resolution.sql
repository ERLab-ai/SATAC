-- Canonical resolution: published claim links, never destructive entity merging.
BEGIN;
INSERT INTO knowledge.predicate VALUES ('CANONICAL_IDENTITY',ARRAY['*'],ARRAY['*'],false);
ALTER TABLE knowledge.claim_version ADD COLUMN identity_decision_id uuid REFERENCES knowledge.identity_decision;
ALTER TABLE knowledge.claim_version ADD CONSTRAINT identity_link_decision_required CHECK (
 (predicate='CANONICAL_IDENTITY' AND identity_decision_id IS NOT NULL AND conflict_group_id IS NULL)
 OR (predicate<>'CANONICAL_IDENTITY' AND identity_decision_id IS NULL));
CREATE UNIQUE INDEX identity_link_one_per_decision ON knowledge.claim_version(identity_decision_id) WHERE identity_decision_id IS NOT NULL;
CREATE FUNCTION knowledge.validate_identity_link() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,knowledge AS $$
 BEGIN
 IF NEW.predicate<>'CANONICAL_IDENTITY' THEN RETURN NEW; END IF;
 PERFORM pg_advisory_xact_lock(716032);
 IF NOT EXISTS (
 SELECT 1 FROM knowledge.identity_decision d JOIN knowledge.identity_candidate p ON p.id=d.candidate_id
 JOIN knowledge.source_version s ON s.id=d.source_version_id
 WHERE d.id=NEW.identity_decision_id AND d.decision='same_entity'
 AND NEW.subject_id<>NEW.object_id AND least(NEW.subject_id,NEW.object_id)=p.entity_low
 AND greatest(NEW.subject_id,NEW.object_id)=p.entity_high
 AND NOT s.restricted AND NOT EXISTS(SELECT 1 FROM knowledge.source_revocation x WHERE x.source_version_id=s.id)
 AND NOT EXISTS(SELECT 1 FROM knowledge.identity_decision next WHERE next.previous_id=d.id)
 ) THEN RAISE EXCEPTION 'invalid reviewed identity link' USING ERRCODE='23514'; END IF;
 RETURN NEW;
 END $$;
CREATE TRIGGER identity_link_validation BEFORE INSERT ON knowledge.claim_version
 FOR EACH ROW EXECUTE FUNCTION knowledge.validate_identity_link();

-- Staging chooses an explicit direction; it does not activate a release.
CREATE FUNCTION knowledge.stage_identity_link(d uuid,alias_id uuid,canonical_id uuid) RETURNS uuid
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,knowledge AS $$
 DECLARE c uuid:=gen_random_uuid(); v uuid:=gen_random_uuid(); s uuid; loc text; existing knowledge.claim_version;
 BEGIN
 PERFORM pg_advisory_xact_lock(716032);
 SELECT * INTO existing FROM knowledge.claim_version WHERE identity_decision_id=d;
 IF FOUND THEN
   IF existing.subject_id IS DISTINCT FROM alias_id OR existing.object_id IS DISTINCT FROM canonical_id
   OR EXISTS(SELECT 1 FROM knowledge.withdrawal WHERE version_id=existing.id)
   OR EXISTS(SELECT 1 FROM knowledge.identity_decision WHERE previous_id=d)
   THEN RAISE EXCEPTION 'identity link already staged or withdrawn' USING ERRCODE='23514'; END IF;
   RETURN existing.id;
 END IF;
 SELECT source_version_id,locator INTO STRICT s,loc FROM knowledge.identity_decision WHERE id=d;
 INSERT INTO knowledge.claim VALUES(c);
 INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_id,verification_status,identity_decision_id)
 VALUES(v,c,alias_id,'CANONICAL_IDENTITY',canonical_id,'verified',d);
 INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator,stance)
 VALUES(gen_random_uuid(),v,s,loc,'supports');
 RETURN v;
 END $$;
-- A superseding decision invalidates the previous link globally, including archives.
-- It never changes either entity or rewrites a release. No new link is staged implicitly.
CREATE FUNCTION knowledge.withdraw_superseded_identity_link() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,knowledge AS $$
 BEGIN
 INSERT INTO knowledge.withdrawal(version_id,reason,actor)
 SELECT id,'superseded identity decision',NEW.reviewer FROM knowledge.claim_version WHERE identity_decision_id=NEW.previous_id
 ON CONFLICT DO NOTHING;
 RETURN NEW;
 END $$;
CREATE TRIGGER identity_link_split AFTER INSERT ON knowledge.identity_decision
 FOR EACH ROW EXECUTE FUNCTION knowledge.withdraw_superseded_identity_link();
CREATE OR REPLACE FUNCTION knowledge.publish(r uuid, ids uuid[]) RETURNS text LANGUAGE plpgsql SECURITY DEFINER
 SET search_path=pg_catalog,knowledge,public AS $$
 DECLARE h text; active uuid;
 BEGIN
 PERFORM pg_advisory_xact_lock(716032);
 SELECT release_id INTO active FROM knowledge.current_release;
 IF r IS NULL OR ids IS NULL OR array_position(ids,NULL) IS NOT NULL OR
 (SELECT count(DISTINCT x) FROM unnest(ids) x)<>cardinality(ids) OR
 (SELECT count(DISTINCT claim_id) FROM knowledge.claim_version WHERE id=ANY(ids))<>cardinality(ids)
 OR EXISTS(SELECT 1 FROM knowledge.claim_version c WHERE c.id=ANY(ids) AND
 (c.synthetic OR c.restricted OR c.verification_status='known_incorrect' OR EXISTS(SELECT 1 FROM knowledge.withdrawal w WHERE w.version_id=c.id)))
 THEN RAISE EXCEPTION 'invalid release membership' USING ERRCODE='23514'; END IF;
 -- Identity resolution is deliberately limited to disjoint reviewed pairs.
 IF EXISTS (
   SELECT endpoint FROM (
     SELECT c.subject_id AS endpoint FROM knowledge.claim_version c WHERE c.id=ANY(ids) AND c.predicate='CANONICAL_IDENTITY'
     UNION ALL
     SELECT c.object_id AS endpoint FROM knowledge.claim_version c WHERE c.id=ANY(ids) AND c.predicate='CANONICAL_IDENTITY'
   ) endpoints GROUP BY endpoint HAVING count(*)>1
 ) THEN RAISE EXCEPTION 'overlapping canonical identity pairs' USING ERRCODE='23514'; END IF;
 IF EXISTS (
   SELECT 1 FROM knowledge.claim_version c WHERE c.id=ANY(ids) AND c.predicate='CANONICAL_IDENTITY'
   AND NOT EXISTS (
     SELECT 1 FROM knowledge.identity_decision d JOIN knowledge.source_version s ON s.id=d.source_version_id
     JOIN knowledge.evidence e ON e.version_id=c.id AND e.source_version_id=s.id AND e.locator=d.locator AND e.stance='supports'
     WHERE d.id=c.identity_decision_id AND NOT s.restricted
     AND NOT EXISTS(SELECT 1 FROM knowledge.source_revocation x WHERE x.source_version_id=s.id)
     AND NOT EXISTS(SELECT 1 FROM knowledge.identity_decision next WHERE next.previous_id=d.id)
   )
 ) THEN RAISE EXCEPTION 'identity decision no longer eligible' USING ERRCODE='23514'; END IF;
 -- A staged successor is not publication authorization. Carry forward active versions;
 -- do not newly admit an already superseded version from staging or an old release.
 IF EXISTS(SELECT 1 FROM knowledge.claim_version c WHERE c.id=ANY(ids)
 AND EXISTS(SELECT 1 FROM knowledge.claim_version s WHERE s.supersedes_id=c.id)
 AND NOT EXISTS(SELECT 1 FROM knowledge.release_member m WHERE m.release_id=active AND m.version_id=c.id))
 THEN RAISE EXCEPTION 'superseded version cannot be newly admitted' USING ERRCODE='23514'; END IF;
 -- Materialize once so hash and members use the same snapshot even if staging changes concurrently.
 -- Existing public payloads are the authority for the same version ID.
 -- Prefer the current release; for an absent but formerly published version,
 -- reuse the latest historical payload, never mutable staging.
 WITH snapshot AS MATERIALIZED (
 SELECT x AS id,coalesce(prior.payload,knowledge.project(x)) AS payload
 FROM unnest(ids) x
 LEFT JOIN LATERAL (
 SELECT m.payload FROM knowledge.release_member m JOIN knowledge.release old_r ON old_r.id=m.release_id
 WHERE m.version_id=x
 ORDER BY (m.release_id=active) DESC NULLS LAST,old_r.created_at DESC,old_r.id DESC LIMIT 1
 ) prior ON true
 ),
 inserted AS (INSERT INTO knowledge.release(id,manifest_sha256)
 SELECT r,encode(public.digest(convert_to(coalesce(jsonb_agg(payload ORDER BY id),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex') FROM snapshot RETURNING manifest_sha256),
 members AS (INSERT INTO knowledge.release_member SELECT r,s.id,s.payload FROM snapshot s CROSS JOIN inserted RETURNING version_id)
 SELECT manifest_sha256 INTO h FROM inserted;
 INSERT INTO knowledge.current_release VALUES(true,r) ON CONFLICT(singleton) DO UPDATE SET release_id=excluded.release_id;
 RETURN h;
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
 )
 AND NOT EXISTS (
   SELECT 1 FROM knowledge.embedded_url_revocation u
   WHERE m.payload->>'predicate' IN ('ARTICLE','EDITORIAL_LINK','EDITORIAL_JOURNEY','DIRECTORY_ENTRY','ROUTE_SEGMENT','HISTORICAL_SNAPSHOT','GEOLOGY_RECORD','CELL_METRIC','EXTENDED_TOPIC')
     AND jsonb_path_exists(m.payload - 'references' - 'geometries',
       'strict $.** ? (@.type() == "string" && @ == $url)', jsonb_build_object('url',u.url))
 )
 AND (m.payload->>'predicate' <> 'CANONICAL_IDENTITY' OR EXISTS (
   SELECT 1 FROM knowledge.claim_version c JOIN knowledge.identity_decision d ON d.id=c.identity_decision_id
   JOIN knowledge.source_version s ON s.id=d.source_version_id
   WHERE c.id=m.version_id AND NOT s.restricted
   AND NOT EXISTS(SELECT 1 FROM knowledge.source_revocation x WHERE x.source_version_id=s.id)
   AND NOT EXISTS(SELECT 1 FROM knowledge.identity_decision next WHERE next.previous_id=d.id)
   AND refs.kept @> jsonb_build_array(jsonb_build_object('source_version_id',s.id,'locator',d.locator,'stance','supports'))
 ));

REVOKE ALL ON FUNCTION knowledge.validate_identity_link(),knowledge.stage_identity_link(uuid,uuid,uuid),knowledge.withdraw_superseded_identity_link() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION knowledge.stage_identity_link(uuid,uuid,uuid) TO satac_curator;
COMMIT;
