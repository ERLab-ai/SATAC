-- Test historical/current projections; roll back all fixture writes.
BEGIN;
DO $$
DECLARE
 p uuid:=gen_random_uuid(); c uuid:=gen_random_uuid(); v uuid:=gen_random_uuid();
 c2 uuid:=gen_random_uuid(); v2 uuid:=gen_random_uuid();
 s1 uuid:=gen_random_uuid(); s2 uuid:=gen_random_uuid();
 r1 uuid:=gen_random_uuid(); r2 uuid:=gen_random_uuid(); r3 uuid:=gen_random_uuid();
 g1 uuid:='00000000-0000-0000-0000-000000000010'; g2 uuid:='00000000-0000-0000-0000-000000000011'; g3 uuid:='00000000-0000-0000-0000-000000000012';
 archived jsonb; visible jsonb; hash1 text; hash2 text;
BEGIN
 INSERT INTO knowledge.entity VALUES(p,'Place');
 INSERT INTO knowledge.claim VALUES(c),(c2);
 INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language)
 VALUES(v,c,p,'NAME','Access fixture','en'),(v2,c2,p,'NAME','Second fixture','en');
 INSERT INTO knowledge.source_version(id,title) VALUES(s1,'Source to withhold'),(s2,'Source to keep');
 INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator) VALUES
 (gen_random_uuid(),v,s1,'sensitive locator'),(gen_random_uuid(),v,s2,'safe locator'),(gen_random_uuid(),v2,s1,'another locator');
 INSERT INTO knowledge.geometry_attestation(id,version_id,role,geom,precision_label,derivation) VALUES
 (g1,v,'location',public.ST_SetSRID(public.ST_Point(39,21),4326),'exact','fixture'),
 (g2,v,'location',public.ST_SetSRID(public.ST_Point(39,21),4326),'approximate','fixture'),
 (g3,v,'location',public.ST_SetSRID(public.ST_Point(44,24),4326),'exact','fixture');
 hash1:=knowledge.publish(r1,ARRAY[v,v2]);
 hash2:=knowledge.publish(r2,ARRAY[v2,v]);
 IF hash1<>hash2 THEN RAISE EXCEPTION 'fixture manifest mismatch'; END IF;
 SELECT payload INTO STRICT archived FROM knowledge.release_member WHERE release_id=r1 AND version_id=v;
 IF jsonb_array_length(archived->'references')<>2 OR jsonb_array_length(archived->'geometries')<>3 THEN RAISE EXCEPTION 'fixture projection mismatch'; END IF;
 -- Mutation in staging must not change which archived geometry is selected.
 UPDATE knowledge.geometry_attestation SET geom=public.ST_SetSRID(public.ST_Point(40,22),4326) WHERE id=g1;
 BEGIN PERFORM knowledge.revoke_geometry(r1,v,0,'bad','fixture');RAISE EXCEPTION 'zero ordinal accepted';EXCEPTION WHEN check_violation THEN NULL;END;
 BEGIN PERFORM knowledge.revoke_geometry(r1,v,99,'bad','fixture');RAISE EXCEPTION 'missing geometry accepted';EXCEPTION WHEN check_violation THEN NULL;END;
 BEGIN PERFORM knowledge.revoke_source(s1,' ','fixture');RAISE EXCEPTION 'empty reason accepted';EXCEPTION WHEN check_violation THEN NULL;END;
 PERFORM knowledge.revoke_source(s1,'access policy','fixture curator');
 PERFORM knowledge.revoke_source(s1,'repeat','fixture curator');
 PERFORM knowledge.revoke_geometry(r1,v,1,'access policy','fixture curator');
 PERFORM knowledge.revoke_geometry(r2,v,2,'repeat geometry','fixture curator');
 IF (SELECT count(*) FROM knowledge.source_revocation WHERE source_version_id=s1)<>1 OR (SELECT count(*) FROM knowledge.geometry_revocation WHERE version_id=v)<>1 THEN RAISE EXCEPTION 'revocation not idempotent'; END IF;
 SELECT payload INTO STRICT visible FROM public_read.release_claims WHERE release_id=r1 AND version_id=v;
 IF visible->'references' IS DISTINCT FROM (SELECT jsonb_agg(e) FROM jsonb_array_elements(archived->'references') e WHERE e->>'source_version_id'=s2::text)
 OR jsonb_array_length(visible->'geometries') IS DISTINCT FROM 1
 OR visible->'geometries'->0->'geometry'->'coordinates' IS DISTINCT FROM '[44,24]'::jsonb
 OR visible->>'object_text' IS DISTINCT FROM 'Access fixture' THEN RAISE EXCEPTION 'selective masking failed'; END IF;
 IF (SELECT payload FROM public_read.release_claims WHERE release_id=r2 AND version_id=v) IS DISTINCT FROM visible THEN RAISE EXCEPTION 'release inconsistency'; END IF;
 IF (SELECT payload FROM public_read.release_claims WHERE release_id=r1 AND version_id=v2) ? 'references' THEN RAISE EXCEPTION 'source leaked in second claim'; END IF;
 IF (SELECT count(*) FROM public_read.entity_names WHERE release_id=r1 AND version_id IN(v,v2))<>2 THEN RAISE EXCEPTION 'name search unnecessarily withheld'; END IF;
 IF knowledge.publish(r3,ARRAY[v,v2])<>hash1 OR (SELECT payload FROM public_read.release_claims WHERE release_id=r3 AND version_id=v) IS DISTINCT FROM visible THEN RAISE EXCEPTION 'carry-forward resurrected restricted material'; END IF;
 IF (SELECT payload FROM knowledge.release_member WHERE release_id=r1 AND version_id=v) IS DISTINCT FROM archived OR knowledge.verify_release(r1) IS DISTINCT FROM true OR knowledge.verify_release(r3) IS DISTINCT FROM true THEN RAISE EXCEPTION 'archive changed'; END IF;
 PERFORM knowledge.revoke_source(s2,'second access decision','fixture curator');
 PERFORM knowledge.revoke_geometry(r1,v,3,'second geometry decision','fixture curator');
 SELECT payload INTO STRICT visible FROM public_read.current_claims WHERE version_id=v;
 IF visible ?| ARRAY['references','geometries','reason','actor'] THEN RAISE EXCEPTION 'empty or administrative fields leaked'; END IF;
 PERFORM knowledge.withhold_version(v2,'embedded access decision','fixture curator');
 IF EXISTS(SELECT 1 FROM public_read.entity_names WHERE version_id=v2) OR EXISTS(SELECT 1 FROM knowledge.review_task WHERE version_id=v2 AND reason='correction') THEN RAISE EXCEPTION 'withholding semantics failed'; END IF;
 BEGIN PERFORM knowledge.publish(gen_random_uuid(),ARRAY[v,v2]);RAISE EXCEPTION 'withheld version admitted';EXCEPTION WHEN check_violation THEN NULL;END;
 BEGIN DELETE FROM knowledge.source_revocation WHERE source_version_id=s1;RAISE EXCEPTION 'mutable access audit';EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL;END;
 BEGIN DELETE FROM knowledge.geometry_revocation WHERE version_id=v;RAISE EXCEPTION 'mutable geometry audit';EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL;END;
END $$;
DO $$
DECLARE fn text;
BEGIN
 FOREACH fn IN ARRAY ARRAY['knowledge.revoke_source(uuid,text,text)','knowledge.revoke_geometry(uuid,uuid,integer,text,text)','knowledge.withhold_version(uuid,text,text)'] LOOP
 IF has_function_privilege('satac_reader',fn,'EXECUTE') OR has_function_privilege('satac_publisher',fn,'EXECUTE') OR NOT has_function_privilege('satac_curator',fn,'EXECUTE') THEN RAISE EXCEPTION 'access function permissions'; END IF;
 END LOOP;
 IF has_table_privilege('satac_reader','knowledge.source_revocation','SELECT') OR has_table_privilege('satac_reader','knowledge.geometry_revocation','SELECT') THEN RAISE EXCEPTION 'reader audit access'; END IF;
END $$;
ROLLBACK;
SELECT 'PASS: selective source/geometry revocation, immutable archives, cross-release masking, whole-version withholding and roles' AS result;
