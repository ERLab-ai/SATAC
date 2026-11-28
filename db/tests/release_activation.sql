-- Disposable fixture, rolled back. Exercises correction and access masks.
BEGIN;
DO $$
DECLARE p uuid:=gen_random_uuid(); c1 uuid:=gen_random_uuid(); c2 uuid:=gen_random_uuid(); c3 uuid:=gen_random_uuid();
 v1 uuid:=gen_random_uuid(); v2 uuid:=gen_random_uuid(); v3 uuid:=gen_random_uuid(); v4 uuid:=gen_random_uuid();
 s uuid:=gen_random_uuid(); r1 uuid:=gen_random_uuid(); r2 uuid:=gen_random_uuid(); fake uuid:=gen_random_uuid();
 h1 text; h2 text; event_id uuid; stored jsonb; fake_payload jsonb;
BEGIN
 INSERT INTO knowledge.entity VALUES(p,'Place');
 INSERT INTO knowledge.claim VALUES(c1),(c2),(c3);
 INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language)
 VALUES(v1,c1,p,'NAME','Old fixture','en'),(v2,c2,p,'NAME','Retained fixture','en');
 INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language,synthetic)
 VALUES(v3,c3,p,'NAME','Synthetic fixture','en',true);
 INSERT INTO knowledge.source_version(id,title) VALUES(s,'Source fixture');
 INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator) VALUES(gen_random_uuid(),v2,s,'private fixture');
 INSERT INTO knowledge.geometry_attestation(id,version_id,role,geom,precision_label,derivation)
 VALUES(gen_random_uuid(),v2,'location',public.ST_SetSRID(public.ST_Point(39,21),4326),'exact','fixture');
 h1:=knowledge.publish(r1,ARRAY[v1,v2]);
 SELECT payload INTO STRICT stored FROM knowledge.release_member WHERE release_id=r1 AND version_id=v2;
 INSERT INTO knowledge.claim_version(id,claim_id,supersedes_id,subject_id,predicate,object_text,language)
 VALUES(v4,c1,v1,p,'NAME','Corrected fixture','en');
 h2:=knowledge.correct(v1,v4,r2,'known error','fixture basis','fixture curator');
 PERFORM knowledge.revoke_source(s,'source access','fixture curator');
 PERFORM knowledge.revoke_geometry(r1,v2,1,'geometry access','fixture curator');
 -- Invalid/stale approval cannot change pointer or create an audit event.
 BEGIN PERFORM knowledge.activate_release(r1,r1,h1,'stale','fixture');RAISE EXCEPTION 'stale activation accepted';EXCEPTION WHEN check_violation THEN NULL;END;
 BEGIN PERFORM knowledge.activate_release(r2,r1,repeat('0',64),'bad hash','fixture');RAISE EXCEPTION 'bad hash accepted';EXCEPTION WHEN check_violation THEN NULL;END;
 BEGIN PERFORM knowledge.activate_release(r2,r1,h1,' ','fixture');RAISE EXCEPTION 'blank reason accepted';EXCEPTION WHEN check_violation THEN NULL;END;
 BEGIN PERFORM knowledge.activate_release(r2,r2,h2,'same','fixture');RAISE EXCEPTION 'same release accepted';EXCEPTION WHEN check_violation THEN NULL;END;
 -- Deliberately construct a correctly hashed synthetic test archive; publisher
 -- must reject activation even though archive checksum is valid.
 fake_payload:=knowledge.project(v3);
 INSERT INTO knowledge.release(id,manifest_sha256) VALUES(fake,encode(public.digest(convert_to(jsonb_build_array(fake_payload)::text,'UTF8'),'sha256'),'hex'));
 INSERT INTO knowledge.release_member VALUES(fake,v3,fake_payload);
 BEGIN PERFORM knowledge.activate_release(r2,fake,(SELECT manifest_sha256 FROM knowledge.release WHERE id=fake),'synthetic','fixture');RAISE EXCEPTION 'synthetic archive accepted';EXCEPTION WHEN check_violation THEN NULL;END;
 IF (SELECT release_id FROM knowledge.current_release)<>r2 OR EXISTS(SELECT 1 FROM knowledge.release_activation WHERE previous_release_id=r2) THEN RAISE EXCEPTION 'failed activation mutated state';END IF;
 event_id:=knowledge.activate_release(r2,r1,h1,'rollback fixture','fixture publisher');
 IF (SELECT release_id FROM knowledge.current_release)<>r1 THEN RAISE EXCEPTION 'pointer not restored';END IF;
 IF NOT EXISTS(SELECT 1 FROM knowledge.release_activation WHERE id=event_id AND previous_release_id=r2 AND target_release_id=r1 AND target_manifest_sha256=h1 AND reason='rollback fixture' AND actor='fixture publisher') THEN RAISE EXCEPTION 'activation audit missing';END IF;
 IF EXISTS(SELECT 1 FROM public_read.current_claims WHERE version_id IN(v1,v4,v3)) OR (SELECT count(*) FROM public_read.current_claims WHERE version_id=v2)<>1 THEN RAISE EXCEPTION 'rollback exposed withdrawn or wrong version';END IF;
 IF (SELECT payload FROM public_read.current_claims WHERE version_id=v2) ?| ARRAY['references','geometries'] THEN RAISE EXCEPTION 'rollback exposed revoked fields';END IF;
 IF (SELECT payload FROM knowledge.release_member WHERE release_id=r1 AND version_id=v2) IS DISTINCT FROM stored OR knowledge.verify_release(r1) IS DISTINCT FROM true OR knowledge.verify_release(r2) IS DISTINCT FROM true THEN RAISE EXCEPTION 'archive changed';END IF;
 -- Move forward again; correction stays visible and no new release is made.
 PERFORM knowledge.activate_release(r1,r2,h2,'forward fixture','fixture publisher');
 IF (SELECT release_id FROM knowledge.current_release)<>r2 OR NOT EXISTS(SELECT 1 FROM public_read.current_claims WHERE version_id=v4) OR EXISTS(SELECT 1 FROM public_read.current_claims WHERE version_id=v1) THEN RAISE EXCEPTION 'forward activation failed';END IF;
 BEGIN DELETE FROM knowledge.release_activation WHERE id=event_id;RAISE EXCEPTION 'mutable audit';EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL;END;
END $$;
DO $$ BEGIN
 IF has_function_privilege('satac_reader','knowledge.activate_release(uuid,uuid,text,text,text)','EXECUTE')
 OR has_function_privilege('satac_curator','knowledge.activate_release(uuid,uuid,text,text,text)','EXECUTE')
 OR NOT has_function_privilege('satac_publisher','knowledge.activate_release(uuid,uuid,text,text,text)','EXECUTE')
 OR has_table_privilege('satac_reader','knowledge.release_activation','SELECT')
 THEN RAISE EXCEPTION 'activation privilege leak'; END IF;
END $$;
ROLLBACK;
SELECT 'PASS: audited immutable rollback and forward activation, stale approval and synthetic rejection, continuing withdrawal and selective masking';
