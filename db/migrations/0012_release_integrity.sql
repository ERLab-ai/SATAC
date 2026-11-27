-- Preserve released payloads when creating new knowledge releases.
BEGIN;
CREATE INDEX release_member_version_lookup ON knowledge.release_member(version_id,release_id);
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

-- Verification concerns the immutable stored manifest, not the live withdrawal overlay.
CREATE FUNCTION knowledge.verify_release(r uuid) RETURNS boolean
 LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,knowledge,public AS $$
 SELECT old_r.manifest_sha256=encode(public.digest(convert_to(
 coalesce((SELECT jsonb_agg(m.payload ORDER BY m.version_id) FROM knowledge.release_member m WHERE m.release_id=r),'[]'::jsonb)::text,'UTF8'),'sha256'),'hex')
 FROM knowledge.release old_r WHERE old_r.id=r
 $$;
REVOKE ALL ON FUNCTION knowledge.verify_release(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION knowledge.verify_release(uuid) TO satac_curator,satac_publisher;
-- Existing grants on publish/correct remain intact; no new public access.
COMMIT;
