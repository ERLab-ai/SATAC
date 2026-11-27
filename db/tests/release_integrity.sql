-- Disposable integration fixture. All changes, including the active pointer, roll back.
BEGIN;
DO $$
DECLARE
 person uuid:=gen_random_uuid(); p1 uuid:=gen_random_uuid(); p2 uuid:=gen_random_uuid();
 ca uuid:=gen_random_uuid(); cb uuid:=gen_random_uuid(); cc uuid:=gen_random_uuid(); cd uuid:=gen_random_uuid();
 va uuid:=gen_random_uuid(); vb uuid:=gen_random_uuid(); vc uuid:=gen_random_uuid(); vd uuid:=gen_random_uuid();
 va2 uuid:=gen_random_uuid(); vb2 uuid:=gen_random_uuid();
 src uuid:=gen_random_uuid(); geom_id uuid:=gen_random_uuid();
 r1 uuid:=gen_random_uuid(); r2 uuid:=gen_random_uuid(); r3 uuid:=gen_random_uuid(); r4 uuid:=gen_random_uuid(); r5 uuid:=gen_random_uuid();
 before_b jsonb; before_c jsonb; before_d jsonb; h1 text; h2 text; active_before uuid;
BEGIN
 INSERT INTO knowledge.entity VALUES(person,'Person'),(p1,'Place'),(p2,'Place');
 INSERT INTO knowledge.claim VALUES(ca),(cb),(cc),(cd);
 INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_id)
 VALUES(va,ca,person,'BORN_IN',p1),(vb,cb,person,'LIVED_IN',p1),(vc,cc,person,'TRAVELED_TO',p1),(vd,cd,person,'LIVED_IN',p2);
 INSERT INTO knowledge.temporal_extent VALUES(vb,'bounded',100,100,'bounded',200,200,'original','CE','year','fixture');
 INSERT INTO knowledge.geometry_attestation(id,version_id,role,geom,precision_label,derivation)
 VALUES(geom_id,vb,'location',public.ST_SetSRID(public.ST_Point(39,21),4326),'approximate','fixture');
 h1:=knowledge.publish(r1,ARRAY[va,vb,vc,vd]);
 SELECT payload INTO STRICT before_b FROM knowledge.release_member WHERE release_id=r1 AND version_id=vb;
 SELECT payload INTO STRICT before_c FROM knowledge.release_member WHERE release_id=r1 AND version_id=vc;
 SELECT payload INTO STRICT before_d FROM knowledge.release_member WHERE release_id=r1 AND version_id=vd;
 IF knowledge.verify_release(r1) IS DISTINCT FROM true THEN RAISE EXCEPTION 'original manifest mismatch'; END IF;
 -- Mutable staging now differs from the published payload in every dependent dimension.
 UPDATE knowledge.temporal_extent SET start_low=101,start_high=101,original_text='staged' WHERE version_id=vb;
 UPDATE knowledge.geometry_attestation SET geom=public.ST_SetSRID(public.ST_Point(41,24),4326) WHERE id=geom_id;
 INSERT INTO knowledge.source_version(id,title) VALUES(src,'Late staging source');
 INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator) VALUES(gen_random_uuid(),vb,src,'late page');
 INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator) VALUES(gen_random_uuid(),vd,src,'late page');
 IF knowledge.project(vb)=before_b OR knowledge.project(vd)=before_d THEN RAISE EXCEPTION 'fixture failed to change projection'; END IF;
 -- Ordinary publication with same members cannot absorb staging drift.
 h2:=knowledge.publish(r2,ARRAY[vd,vc,vb,va]);
 IF h1<>h2 OR knowledge.verify_release(r2) IS DISTINCT FROM true THEN RAISE EXCEPTION 'same membership drifted'; END IF;
 -- A draft successor of an unrelated record must not be silently published or prevent a correction.
 INSERT INTO knowledge.claim_version(id,claim_id,supersedes_id,subject_id,predicate,object_id)
 VALUES(va2,ca,va,person,'BORN_IN',p2),(vb2,cb,vb,person,'LIVED_IN',p2);
 -- A withdrawn, unrelated record must not be resurrected.
 PERFORM knowledge.flag_incorrect(vc,'unknown correction','fixture');
 SELECT release_id INTO active_before FROM knowledge.current_release;
 BEGIN
 PERFORM knowledge.correct(va,va2,r2,'correct location','fixture basis','fixture actor');
 RAISE EXCEPTION 'duplicate release accepted';
 EXCEPTION WHEN unique_violation THEN NULL;
 END;
 IF (SELECT release_id FROM knowledge.current_release)<>active_before OR EXISTS(SELECT 1 FROM knowledge.correction WHERE old_id=va) OR EXISTS(SELECT 1 FROM knowledge.withdrawal WHERE version_id=va)
 THEN RAISE EXCEPTION 'failed correction changed state'; END IF;
 PERFORM knowledge.correct(va,va2,r3,'correct location','fixture basis','fixture actor');
 IF (SELECT count(*) FROM knowledge.release_member WHERE release_id=r3)<>3 THEN RAISE EXCEPTION 'wrong successor membership'; END IF;
 IF (SELECT payload FROM knowledge.release_member WHERE release_id=r3 AND version_id=vb) IS DISTINCT FROM before_b
 OR (SELECT payload FROM knowledge.release_member WHERE release_id=r3 AND version_id=vd) IS DISTINCT FROM before_d
 THEN RAISE EXCEPTION 'unrelated payload drift'; END IF;
 IF EXISTS(SELECT 1 FROM knowledge.release_member WHERE release_id=r3 AND version_id IN (va,vc,vb2)) THEN RAISE EXCEPTION 'unexpected version admitted'; END IF;
 IF NOT EXISTS(SELECT 1 FROM knowledge.release_member WHERE release_id=r3 AND version_id=va2 AND payload->>'object_id'=p2::text)
 THEN RAISE EXCEPTION 'replacement not projected'; END IF;
 IF EXISTS(SELECT 1 FROM public_read.release_claims WHERE version_id IN (va,vc)) THEN RAISE EXCEPTION 'withdrawn historical payload visible'; END IF;
 IF (SELECT payload FROM knowledge.release_member WHERE release_id=r1 AND version_id=vc) IS DISTINCT FROM before_c THEN RAISE EXCEPTION 'archive mutated'; END IF;
 IF knowledge.verify_release(r1) IS DISTINCT FROM true OR knowledge.verify_release(r3) IS DISTINCT FROM true THEN RAISE EXCEPTION 'manifest verification failed'; END IF;
 IF NOT EXISTS(SELECT 1 FROM knowledge.correction WHERE old_id=va AND new_id=va2 AND reason='correct location' AND basis='fixture basis' AND actor='fixture actor')
 THEN RAISE EXCEPTION 'missing correction audit'; END IF;
 -- A formerly published, non-superseded version can re-enter with its last published payload.
 PERFORM knowledge.publish(r4,ARRAY[va2]);
 PERFORM knowledge.publish(r5,ARRAY[va2,vd]);
 IF (SELECT payload FROM knowledge.release_member WHERE release_id=r5 AND version_id=vd) IS DISTINCT FROM before_d THEN RAISE EXCEPTION 'reintroduced version drift'; END IF;
 BEGIN PERFORM knowledge.publish(gen_random_uuid(),ARRAY[va2,vb,vd]);RAISE EXCEPTION 'newly admitted superseded version';EXCEPTION WHEN check_violation THEN NULL;END;
 BEGIN PERFORM knowledge.publish(gen_random_uuid(),ARRAY[va,vd]);RAISE EXCEPTION 'withdrawn version admitted';EXCEPTION WHEN check_violation THEN NULL;END;
 IF (SELECT release_id FROM knowledge.current_release)<>r5 THEN RAISE EXCEPTION 'invalid publish moved pointer'; END IF;
 IF knowledge.verify_release(r5) IS DISTINCT FROM true OR knowledge.verify_release(gen_random_uuid()) IS NOT NULL THEN RAISE EXCEPTION 'verification contract'; END IF;
END $$;
DO $$ BEGIN
 IF has_function_privilege('satac_reader','knowledge.verify_release(uuid)','EXECUTE') OR has_function_privilege('satac_reader','knowledge.publish(uuid,uuid[])','EXECUTE') THEN RAISE EXCEPTION 'reader permission leak';END IF;
 IF NOT has_function_privilege('satac_curator','knowledge.verify_release(uuid)','EXECUTE') OR NOT has_function_privilege('satac_publisher','knowledge.verify_release(uuid)','EXECUTE') THEN RAISE EXCEPTION 'missing audit permission';END IF;
END $$;
ROLLBACK;
SELECT 'PASS: immutable carry-forward, re-admission, staged successor isolation, correction atomicity, withdrawal and stored manifest verification' AS result;
