-- Disposable fixture, rollback all invented identities.
BEGIN;
DO $$
DECLARE a uuid:=gen_random_uuid(); b uuid:=gen_random_uuid(); p uuid:=gen_random_uuid();
 s uuid:=gen_random_uuid(); x uuid; y uuid; c uuid; d uuid; e uuid;
BEGIN
 INSERT INTO knowledge.entity VALUES(a,'Place'),(b,'Place'),(p,'Person');
 INSERT INTO knowledge.source_version(id,title) VALUES(s,'Identity fixture');
 x:=knowledge.assert_external_identity(a,'fixture-a','42',s,'p. 1','fixture');
 IF knowledge.assert_external_identity(a,'fixture-a','42',s,'p. 1','fixture')<>x THEN RAISE EXCEPTION 'assertion not idempotent'; END IF;
 y:=knowledge.assert_external_identity(b,'fixture-a','42',s,'p. 2','fixture');
 PERFORM knowledge.assert_external_identity(a,'fixture-b','42',s,NULL,'fixture');
 IF x=y OR (SELECT count(*) FROM knowledge.external_identity_assertion WHERE namespace='fixture-a' AND external_id='42')<>2 THEN RAISE EXCEPTION 'collision silently merged'; END IF;
 BEGIN
 PERFORM knowledge.assert_external_identity(a,'fixture-a','42',s,'different locator','fixture');
 RAISE EXCEPTION 'changed assertion accepted'; EXCEPTION WHEN check_violation THEN NULL; END;
 c:=knowledge.propose_identity(a,b,'fixture hypothesis','fixture');
 IF knowledge.propose_identity(b,a,'reverse fixture','fixture')<>c THEN RAISE EXCEPTION 'duplicate pair'; END IF;
 BEGIN PERFORM knowledge.propose_identity(a,p,'cross-kind','fixture'); RAISE EXCEPTION 'cross-kind candidate'; EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN PERFORM knowledge.decide_identity(c,NULL,'same_entity','no basis','fixture',NULL,NULL);
 RAISE EXCEPTION 'unsupported same-entity decision'; EXCEPTION WHEN check_violation THEN NULL; END;
 d:=knowledge.decide_identity(c,NULL,'same_entity','fixture source comparison','fixture',s,'p. 1');
 BEGIN PERFORM knowledge.decide_identity(c,NULL,'distinct_entities','stale','fixture',NULL,NULL);
 RAISE EXCEPTION 'stale decision accepted'; EXCEPTION WHEN check_violation THEN NULL; END;
 e:=knowledge.decide_identity(c,d,'undetermined','reconsidered fixture','fixture',NULL,NULL);
 IF NOT EXISTS(SELECT 1 FROM knowledge.identity_decision WHERE id=e AND previous_id=d)
 OR (SELECT count(*) FROM knowledge.entity WHERE id IN (a,b))<>2
 OR (SELECT count(*) FROM knowledge.identity_decision WHERE candidate_id=c)<>2
 THEN RAISE EXCEPTION 'decision history or entity preservation failed'; END IF;
 BEGIN DELETE FROM knowledge.identity_decision WHERE id=d; RAISE EXCEPTION 'decision mutated'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END;
END $$;
DO $$ BEGIN
 IF has_table_privilege('satac_reader','knowledge.external_identity_assertion','SELECT')
 OR has_table_privilege('satac_reader','knowledge.identity_candidate','SELECT')
 OR has_function_privilege('satac_reader','knowledge.decide_identity(uuid,uuid,text,text,text,uuid,text)','EXECUTE')
 OR NOT has_function_privilege('satac_curator','knowledge.decide_identity(uuid,uuid,text,text,text,uuid,text)','EXECUTE')
 THEN RAISE EXCEPTION 'identity privilege boundary failed'; END IF;
END $$;
ROLLBACK;
SELECT 'PASS: qualified identity assertions, collisions, explicit review, stale decision rejection and preserved entities';
