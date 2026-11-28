-- Canonical identity: qualified assertions and reviewed proposals, not destructive merges.
BEGIN;
CREATE TABLE knowledge.external_identity_assertion (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 entity_id uuid NOT NULL REFERENCES knowledge.entity,
 namespace text NOT NULL CHECK(namespace ~ '^[a-z][a-z0-9._-]{0,63}$'),
 external_id text NOT NULL CHECK(length(external_id) BETWEEN 1 AND 512 AND external_id=btrim(external_id)),
 source_version_id uuid NOT NULL REFERENCES knowledge.source_version,
 locator text CHECK(locator IS NULL OR btrim(locator)<>''),
 actor text NOT NULL CHECK(btrim(actor)<>''),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(entity_id,namespace,external_id,source_version_id)
);
CREATE INDEX external_identity_lookup ON knowledge.external_identity_assertion(namespace,external_id);
CREATE TRIGGER immutable_external_identity BEFORE UPDATE OR DELETE ON knowledge.external_identity_assertion
 FOR EACH ROW EXECUTE FUNCTION knowledge.immutable_row();

CREATE TABLE knowledge.identity_candidate (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 entity_low uuid NOT NULL REFERENCES knowledge.entity,
 entity_high uuid NOT NULL REFERENCES knowledge.entity,
 rationale text NOT NULL CHECK(btrim(rationale)<>''),
 actor text NOT NULL CHECK(btrim(actor)<>''),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(entity_low<entity_high),
 UNIQUE(entity_low,entity_high)
);
CREATE TABLE knowledge.identity_decision (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 candidate_id uuid NOT NULL REFERENCES knowledge.identity_candidate,
 previous_id uuid UNIQUE,
 decision text NOT NULL CHECK(decision IN ('same_entity','distinct_entities','undetermined')),
 rationale text NOT NULL CHECK(btrim(rationale)<>''),
 reviewer text NOT NULL CHECK(btrim(reviewer)<>''),
 source_version_id uuid REFERENCES knowledge.source_version,
 locator text CHECK(locator IS NULL OR (source_version_id IS NOT NULL AND btrim(locator)<>'')),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(id,candidate_id),
 FOREIGN KEY(previous_id,candidate_id) REFERENCES knowledge.identity_decision(id,candidate_id),
 CHECK(decision<>'same_entity' OR (source_version_id IS NOT NULL AND locator IS NOT NULL))
);
CREATE UNIQUE INDEX identity_decision_root ON knowledge.identity_decision(candidate_id) WHERE previous_id IS NULL;
CREATE TRIGGER immutable_identity_candidate BEFORE UPDATE OR DELETE ON knowledge.identity_candidate
 FOR EACH ROW EXECUTE FUNCTION knowledge.immutable_row();
CREATE TRIGGER immutable_identity_decision BEFORE UPDATE OR DELETE ON knowledge.identity_decision
 FOR EACH ROW EXECUTE FUNCTION knowledge.immutable_row();

CREATE FUNCTION knowledge.assert_external_identity(e uuid,ns text,external text,s uuid,loc text,actor_text text) RETURNS uuid
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,knowledge AS $$
 DECLARE found_id uuid; old_locator text;
 BEGIN
 PERFORM pg_advisory_xact_lock(716032);
 INSERT INTO knowledge.external_identity_assertion(entity_id,namespace,external_id,source_version_id,locator,actor)
 VALUES(e,ns,external,s,loc,actor_text)
 ON CONFLICT(entity_id,namespace,external_id,source_version_id) DO NOTHING RETURNING id INTO found_id;
 IF found_id IS NULL THEN
 SELECT id,locator INTO STRICT found_id,old_locator FROM knowledge.external_identity_assertion
 WHERE entity_id=e AND namespace=ns AND external_id=external AND source_version_id=s;
 IF old_locator IS DISTINCT FROM loc THEN RAISE EXCEPTION 'existing identity assertion differs' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN found_id;
 END $$;

CREATE FUNCTION knowledge.propose_identity(a uuid,b uuid,reason_text text,actor_text text) RETURNS uuid
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,knowledge AS $$
 DECLARE found_id uuid; ka text; kb text;
 BEGIN
 PERFORM pg_advisory_xact_lock(716032);
 SELECT kind INTO ka FROM knowledge.entity WHERE id=a;
 SELECT kind INTO kb FROM knowledge.entity WHERE id=b;
 IF a IS NULL OR b IS NULL OR a=b OR ka IS NULL OR kb IS NULL OR ka<>kb
 OR nullif(btrim(reason_text),'') IS NULL OR nullif(btrim(actor_text),'') IS NULL
 THEN RAISE EXCEPTION 'invalid identity proposal' USING ERRCODE='23514'; END IF;
 INSERT INTO knowledge.identity_candidate(entity_low,entity_high,rationale,actor)
 VALUES(least(a,b),greatest(a,b),reason_text,actor_text) ON CONFLICT(entity_low,entity_high) DO NOTHING RETURNING id INTO found_id;
 IF found_id IS NULL THEN SELECT id INTO STRICT found_id FROM knowledge.identity_candidate WHERE entity_low=least(a,b) AND entity_high=greatest(a,b); END IF;
 RETURN found_id;
 END $$;

CREATE FUNCTION knowledge.decide_identity(c uuid,expected uuid,decision_text text,reason_text text,reviewer_text text,s uuid,loc text) RETURNS uuid
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,knowledge AS $$
 DECLARE latest uuid; event_id uuid;
 BEGIN
 PERFORM pg_advisory_xact_lock(716032);
 IF NOT EXISTS(SELECT 1 FROM knowledge.identity_candidate WHERE id=c)
 THEN RAISE EXCEPTION 'unknown identity candidate' USING ERRCODE='23514'; END IF;
 SELECT d.id INTO latest FROM knowledge.identity_decision d WHERE d.candidate_id=c
 AND NOT EXISTS(SELECT 1 FROM knowledge.identity_decision successor WHERE successor.previous_id=d.id);
 IF latest IS DISTINCT FROM expected THEN RAISE EXCEPTION 'stale identity decision' USING ERRCODE='23514'; END IF;
 INSERT INTO knowledge.identity_decision(candidate_id,previous_id,decision,rationale,reviewer,source_version_id,locator)
 VALUES(c,latest,decision_text,reason_text,reviewer_text,s,loc) RETURNING id INTO event_id;
 RETURN event_id;
 END $$;
-- All assertions and decisions are internal. No mutation of entity IDs, crosswalk,
-- claims, release manifests or public resolution occurs in this migration.
REVOKE ALL ON FUNCTION knowledge.assert_external_identity(uuid,text,text,uuid,text,text),knowledge.propose_identity(uuid,uuid,text,text),knowledge.decide_identity(uuid,uuid,text,text,text,uuid,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION knowledge.assert_external_identity(uuid,text,text,uuid,text,text),knowledge.propose_identity(uuid,uuid,text,text),knowledge.decide_identity(uuid,uuid,text,text,text,uuid,text) TO satac_curator;
GRANT SELECT ON knowledge.external_identity_assertion,knowledge.identity_candidate,knowledge.identity_decision TO satac_curator;
COMMIT;
