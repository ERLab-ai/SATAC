-- A12: audited activation of a previously published immutable release.
BEGIN;
CREATE TABLE knowledge.release_activation (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 previous_release_id uuid NOT NULL REFERENCES knowledge.release,
 target_release_id uuid NOT NULL REFERENCES knowledge.release,
 target_manifest_sha256 text NOT NULL CHECK(target_manifest_sha256 ~ '^[0-9a-f]{64}$'),
 reason text NOT NULL CHECK(btrim(reason)<>''),
 actor text NOT NULL CHECK(btrim(actor)<>''),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(previous_release_id<>target_release_id)
);
CREATE TRIGGER immutable_release_activation BEFORE UPDATE OR DELETE ON knowledge.release_activation
 FOR EACH ROW EXECUTE FUNCTION knowledge.immutable_row();

-- expected_current guards against a stale operator decision. Approval also pins
-- target manifest. Restore the pointer only, never staging or access policy.
CREATE FUNCTION knowledge.activate_release(expected_current uuid,target uuid,expected_manifest text,reason_text text,actor_text text)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,knowledge AS $$
 DECLARE active uuid; archived_hash text; event_id uuid;
 BEGIN
 PERFORM pg_advisory_xact_lock(716032);
 SELECT release_id INTO active FROM knowledge.current_release;
 IF active IS NULL OR expected_current IS DISTINCT FROM active OR target IS NULL OR target=active
 OR nullif(btrim(reason_text),'') IS NULL OR nullif(btrim(actor_text),'') IS NULL
 THEN RAISE EXCEPTION 'invalid or stale release activation' USING ERRCODE='23514'; END IF;
 SELECT manifest_sha256 INTO archived_hash FROM knowledge.release WHERE id=target;
 IF archived_hash IS NULL OR expected_manifest IS DISTINCT FROM archived_hash
 OR knowledge.verify_release(target) IS DISTINCT FROM true
 THEN RAISE EXCEPTION 'target release missing or manifest mismatch' USING ERRCODE='23514'; END IF;
 -- Defensive check: even an owner-created benchmark or corrupt archive must
 -- not become current. Withdrawn normal versions remain in the archive and
 -- are excluded by the public view; source/geometry masking stays live.
 IF EXISTS(SELECT 1 FROM knowledge.release_member m JOIN knowledge.claim_version c ON c.id=m.version_id
 WHERE m.release_id=target AND (c.synthetic OR c.restricted OR c.verification_status='known_incorrect'))
 THEN RAISE EXCEPTION 'ineligible target release' USING ERRCODE='23514'; END IF;
 UPDATE knowledge.current_release SET release_id=target WHERE singleton;
 INSERT INTO knowledge.release_activation(previous_release_id,target_release_id,target_manifest_sha256,reason,actor)
 VALUES(active,target,archived_hash,reason_text,actor_text) RETURNING id INTO event_id;
 RETURN event_id;
 END $$;
REVOKE ALL ON FUNCTION knowledge.activate_release(uuid,uuid,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION knowledge.activate_release(uuid,uuid,text,text,text) TO satac_publisher;
GRANT SELECT ON knowledge.release_activation TO satac_curator;
COMMIT;
