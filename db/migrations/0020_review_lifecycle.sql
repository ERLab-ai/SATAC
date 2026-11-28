-- Internal review lifecycle: auditable decisions independent of publication.
BEGIN;
ALTER TABLE knowledge.review ADD CONSTRAINT review_id_version_unique UNIQUE(id,version_id);
CREATE TABLE knowledge.review_event (
 id uuid PRIMARY KEY,
 version_id uuid NOT NULL REFERENCES knowledge.claim_version,
 previous_id uuid UNIQUE,
 UNIQUE(id,version_id),
 FOREIGN KEY(id,version_id) REFERENCES knowledge.review(id,version_id),
 FOREIGN KEY(previous_id,version_id) REFERENCES knowledge.review_event(id,version_id)
);
CREATE UNIQUE INDEX review_event_root ON knowledge.review_event(version_id) WHERE previous_id IS NULL;
CREATE TRIGGER immutable_review_event BEFORE UPDATE OR DELETE ON knowledge.review_event
 FOR EACH ROW EXECUTE FUNCTION knowledge.immutable_row();
CREATE TRIGGER immutable_review BEFORE UPDATE OR DELETE ON knowledge.review
 FOR EACH ROW EXECUTE FUNCTION knowledge.immutable_row();

CREATE FUNCTION knowledge.record_claim_review(v uuid,expected uuid,decision_text text,reason_text text,reviewer_text text)
 RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,knowledge AS $$
 DECLARE latest uuid; event_id uuid:=gen_random_uuid(); original text; previous_decision text;
 BEGIN
 PERFORM pg_advisory_xact_lock(716032);
 SELECT verification_status INTO original FROM knowledge.claim_version WHERE id=v;
 IF original IS NULL OR decision_text IS NULL OR decision_text NOT IN ('verified','review_required','disputed','known_incorrect')
 OR nullif(btrim(reason_text),'') IS NULL OR nullif(btrim(reviewer_text),'') IS NULL
 THEN RAISE EXCEPTION 'invalid claim review' USING ERRCODE='23514'; END IF;
 SELECT e.id,r.decision INTO latest,previous_decision FROM knowledge.review_event e JOIN knowledge.review r ON r.id=e.id
 WHERE e.version_id=v AND NOT EXISTS(SELECT 1 FROM knowledge.review_event s WHERE s.previous_id=e.id);
 IF latest IS DISTINCT FROM expected THEN RAISE EXCEPTION 'stale claim review' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM knowledge.correction WHERE old_id=v)
 THEN RAISE EXCEPTION 'review the successor of corrected version' USING ERRCODE='23514'; END IF;
 IF decision_text<>'known_incorrect' AND (original='known_incorrect' OR previous_decision='known_incorrect' OR
 EXISTS(SELECT 1 FROM knowledge.review_task WHERE version_id=v AND reason='correction' AND resolved_at IS NULL))
 THEN RAISE EXCEPTION 'known error requires correction, not review override' USING ERRCODE='23514'; END IF;
 INSERT INTO knowledge.review(id,version_id,reviewer,decision,rationale)
 VALUES(event_id,v,reviewer_text,decision_text,reason_text);
 INSERT INTO knowledge.review_event(id,version_id,previous_id) VALUES(event_id,v,latest);
 IF decision_text IN ('review_required','disputed') THEN
 INSERT INTO knowledge.review_task(version_id,reason) VALUES(v,'review')
 ON CONFLICT(version_id,reason) DO UPDATE SET resolved_at=NULL;
 ELSE
 UPDATE knowledge.review_task SET resolved_at=clock_timestamp()
 WHERE version_id=v AND reason='review' AND resolved_at IS NULL;
 END IF;
 IF decision_text='known_incorrect' THEN
 PERFORM knowledge.flag_incorrect(v,reason_text,reviewer_text);
 END IF;
 RETURN event_id;
 END $$;

-- Internal state projection only. Publication and epistemic status remain independent.
CREATE VIEW knowledge.claim_review_state AS
 SELECT c.id AS version_id, e.id AS latest_review_id,
 CASE WHEN c.verification_status='known_incorrect'
 OR EXISTS(SELECT 1 FROM knowledge.correction x WHERE x.old_id=c.id)
 OR EXISTS(SELECT 1 FROM knowledge.review_task t WHERE t.version_id=c.id AND t.reason='correction' AND t.resolved_at IS NULL)
 THEN 'known_incorrect' ELSE coalesce(r.decision,c.verification_status) END AS verification_status,
 c.epistemic_status,
 CASE WHEN NOT EXISTS(SELECT 1 FROM knowledge.evidence f WHERE f.version_id=c.id) THEN 'missing'
 WHEN EXISTS(SELECT 1 FROM knowledge.evidence f WHERE f.version_id=c.id AND f.locator IS NULL) THEN 'incomplete'
 ELSE 'available' END AS source_status
 FROM knowledge.claim_version c
 LEFT JOIN knowledge.review_event e ON e.version_id=c.id
 AND NOT EXISTS(SELECT 1 FROM knowledge.review_event s WHERE s.previous_id=e.id)
 LEFT JOIN knowledge.review r ON r.id=e.id;
REVOKE ALL ON FUNCTION knowledge.record_claim_review(uuid,uuid,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION knowledge.record_claim_review(uuid,uuid,text,text,text) TO satac_curator;
GRANT SELECT ON knowledge.review,knowledge.review_event,knowledge.claim_review_state TO satac_curator;
COMMIT;
