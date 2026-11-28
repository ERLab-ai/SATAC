-- Disposable fixture only: review is independent of source and release membership.
BEGIN;
DO $$
DECLARE p uuid:=gen_random_uuid(); c uuid:=gen_random_uuid(); v uuid:=gen_random_uuid(); w uuid:=gen_random_uuid();
 s uuid:=gen_random_uuid(); r1 uuid:=gen_random_uuid(); r2 uuid:=gen_random_uuid(); h text; a uuid; b uuid; d uuid;
BEGIN
 INSERT INTO knowledge.entity VALUES(p,'Place');
 INSERT INTO knowledge.claim VALUES(c);
 INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language)
 VALUES(v,c,p,'NAME','Review fixture','en');
 h:=knowledge.publish(r1,ARRAY[v]);
 a:=knowledge.record_claim_review(v,NULL,'verified','fixture review','fixture curator');
 IF NOT EXISTS(SELECT 1 FROM knowledge.claim_review_state WHERE version_id=v AND verification_status='verified' AND source_status='missing' AND latest_review_id=a)
 OR NOT EXISTS(SELECT 1 FROM knowledge.review_task WHERE version_id=v AND reason='documentation' AND resolved_at IS NULL)
 OR EXISTS(SELECT 1 FROM knowledge.review_task WHERE version_id=v AND reason='review' AND resolved_at IS NULL)
 THEN RAISE EXCEPTION 'verification coupled to documentation'; END IF;
 BEGIN PERFORM knowledge.record_claim_review(v,NULL,'disputed','stale','fixture');
 RAISE EXCEPTION 'stale review accepted'; EXCEPTION WHEN check_violation THEN NULL; END;
 b:=knowledge.record_claim_review(v,a,'disputed','fixture disagreement','fixture curator');
 IF NOT EXISTS(SELECT 1 FROM knowledge.review_task WHERE version_id=v AND reason='review' AND resolved_at IS NULL)
 OR NOT EXISTS(SELECT 1 FROM public_read.release_claims WHERE release_id=r1 AND version_id=v)
 THEN RAISE EXCEPTION 'dispute blocked publication or failed to reopen review'; END IF;
 INSERT INTO knowledge.source_version(id,title) VALUES(s,'Review fixture source');
 INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator) VALUES(gen_random_uuid(),v,s,'p. 1');
 IF NOT EXISTS(SELECT 1 FROM knowledge.claim_review_state WHERE version_id=v AND source_status='available' AND verification_status='disputed')
 OR EXISTS(SELECT 1 FROM knowledge.review_task WHERE version_id=v AND reason='documentation' AND resolved_at IS NULL)
 THEN RAISE EXCEPTION 'documentation state wrong'; END IF;
 IF NOT knowledge.verify_release(r1) OR (SELECT manifest_sha256 FROM knowledge.release WHERE id=r1)<>h
 OR (SELECT payload FROM public_read.release_claims WHERE release_id=r1 AND version_id=v) ?| ARRAY['verification_status','source_status','latest_review_id','review_event','references']
 THEN RAISE EXCEPTION 'immutable public snapshot or privacy failed'; END IF;
 d:=knowledge.record_claim_review(v,b,'known_incorrect','fixture known error','fixture curator');
 IF EXISTS(SELECT 1 FROM public_read.release_claims WHERE release_id=r1 AND version_id=v)
 OR NOT EXISTS(SELECT 1 FROM knowledge.review_task WHERE version_id=v AND reason='correction' AND resolved_at IS NULL)
 THEN RAISE EXCEPTION 'known error not suppressed'; END IF;
 BEGIN PERFORM knowledge.record_claim_review(v,d,'verified','invalid override','fixture');
 RAISE EXCEPTION 'error reapproval accepted'; EXCEPTION WHEN check_violation THEN NULL; END;
 INSERT INTO knowledge.claim_version(id,claim_id,supersedes_id,subject_id,predicate,object_text,language)
 VALUES(w,c,v,p,'NAME','Corrected fixture','en');
 PERFORM knowledge.correct(v,w,r2,'fixture correction','fixture basis','fixture curator');
 IF NOT EXISTS(SELECT 1 FROM public_read.current_claims WHERE version_id=w)
 OR EXISTS(SELECT 1 FROM knowledge.review_task WHERE version_id=v AND resolved_at IS NULL)
 OR NOT EXISTS(SELECT 1 FROM knowledge.claim_review_state WHERE version_id=w AND verification_status='unreviewed')
 THEN RAISE EXCEPTION 'correction successor lifecycle failed'; END IF;
 IF (SELECT count(*) FROM knowledge.review_event WHERE version_id=v)<>3 OR NOT knowledge.verify_release(r1)
 THEN RAISE EXCEPTION 'review history or archive lost'; END IF;
 BEGIN UPDATE knowledge.review SET rationale='changed' WHERE id=a;
 RAISE EXCEPTION 'review mutated'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END;
END $$;
DO $$ BEGIN
 IF has_table_privilege('satac_reader','knowledge.claim_review_state','SELECT')
 OR has_table_privilege('satac_reader','knowledge.review','SELECT')
 OR has_function_privilege('satac_reader','knowledge.record_claim_review(uuid,uuid,text,text,text)','EXECUTE')
 OR NOT has_function_privilege('satac_curator','knowledge.record_claim_review(uuid,uuid,text,text,text)','EXECUTE')
 THEN RAISE EXCEPTION 'review privilege boundary failed'; END IF;
END $$;
ROLLBACK;
SELECT 'PASS: auditable review transitions, independent documentation, error suppression and corrected successor';
