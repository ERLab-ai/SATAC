-- Disposable transaction: reviewed links are explicit, disjoint and reversible.
BEGIN;
DO $$
DECLARE a uuid:=gen_random_uuid(); b uuid:=gen_random_uuid(); c uuid:=gen_random_uuid();
 s uuid:=gen_random_uuid(); p uuid; q uuid; d uuid; e uuid; v uuid; w uuid;
 r1 uuid:=gen_random_uuid(); r2 uuid:=gen_random_uuid(); h text;
BEGIN
 INSERT INTO knowledge.entity VALUES(a,'Place'),(b,'Place'),(c,'Place');
 INSERT INTO knowledge.source_version(id,title) VALUES(s,'Canonical fixture source');
 p:=knowledge.propose_identity(a,b,'fixture pair','fixture');
 d:=knowledge.decide_identity(p,NULL,'same_entity','fixture basis','fixture',s,'p. 1');
 v:=knowledge.stage_identity_link(d,a,b);
 IF knowledge.stage_identity_link(d,a,b)<>v THEN RAISE EXCEPTION 'non-idempotent link'; END IF;
 IF EXISTS(SELECT 1 FROM public_read.release_claims WHERE version_id=v) THEN RAISE EXCEPTION 'staging leaked'; END IF;
 q:=knowledge.propose_identity(b,c,'fixture overlapping pair','fixture');
 e:=knowledge.decide_identity(q,NULL,'same_entity','fixture basis','fixture',s,'p. 2');
 w:=knowledge.stage_identity_link(e,b,c);
 BEGIN PERFORM knowledge.publish(r2,ARRAY[v,w]); RAISE EXCEPTION 'overlapping pairs accepted'; EXCEPTION WHEN check_violation THEN NULL; END;
 h:=knowledge.publish(r1,ARRAY[v]);
 IF NOT EXISTS(SELECT 1 FROM public_read.release_claims WHERE release_id=r1 AND version_id=v AND payload->>'object_id'=b::text)
 OR (SELECT payload FROM public_read.release_claims WHERE release_id=r1 AND version_id=v) ? 'identity_decision_id'
 THEN RAISE EXCEPTION 'public identity projection failed'; END IF;
 PERFORM knowledge.decide_identity(p,d,'distinct_entities','fixture split','fixture',NULL,NULL);
 IF EXISTS(SELECT 1 FROM public_read.release_claims WHERE release_id=r1 AND version_id=v)
 OR NOT EXISTS(SELECT 1 FROM knowledge.withdrawal WHERE version_id=v)
 OR NOT knowledge.verify_release(r1)
 OR (SELECT manifest_sha256 FROM knowledge.release WHERE id=r1)<>h
 OR (SELECT count(*) FROM knowledge.entity WHERE id IN (a,b,c))<>3
 THEN RAISE EXCEPTION 'identity separation failed'; END IF;
 BEGIN PERFORM knowledge.stage_identity_link(d,a,b); RAISE EXCEPTION 'stale decision accepted'; EXCEPTION WHEN check_violation THEN NULL; END;
 PERFORM knowledge.publish(r2,ARRAY[w]);
 PERFORM knowledge.revoke_source(s,'fixture source withholding','fixture');
 IF EXISTS(SELECT 1 FROM public_read.release_claims WHERE release_id=r2 AND version_id=w)
 OR NOT knowledge.verify_release(r2) THEN RAISE EXCEPTION 'source access leak'; END IF;
END $$;
DO $$ BEGIN
 IF has_function_privilege('satac_reader','knowledge.stage_identity_link(uuid,uuid,uuid)','EXECUTE')
 OR NOT has_function_privilege('satac_curator','knowledge.stage_identity_link(uuid,uuid,uuid)','EXECUTE')
 THEN RAISE EXCEPTION 'identity staging privilege boundary failed'; END IF;
END $$;
ROLLBACK;
SELECT 'PASS: reviewed identity staging, disjoint pairs, archive separation, source withholding and stable UUIDs';
