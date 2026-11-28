-- Run against a fresh migrated disposable DB, never production.
BEGIN;
INSERT INTO knowledge.entity VALUES
 ('00000000-0000-0000-0000-000000000001','Person'),
 ('00000000-0000-0000-0000-000000000002','Place'),
 ('00000000-0000-0000-0000-000000000003','Place');
INSERT INTO knowledge.claim VALUES ('10000000-0000-0000-0000-000000000001'),('10000000-0000-0000-0000-000000000002'),('10000000-0000-0000-0000-000000000003');
INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_id,synthetic)
VALUES ('20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000001','BORN_IN','00000000-0000-0000-0000-000000000002',false),
('20000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001','BORN_IN','00000000-0000-0000-0000-000000000003',false),
('20000000-0000-0000-0000-000000000003','10000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000001','BORN_IN','00000000-0000-0000-0000-000000000002',true);
INSERT INTO knowledge.temporal_extent VALUES ('20000000-0000-0000-0000-000000000001','bounded',401,500,'bounded',600,650,'fixture','CE','year','test');
INSERT INTO knowledge.geometry_attestation(id,version_id,role,geom,precision_label,derivation,restricted) VALUES
 ('30000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','location',ST_SetSRID(ST_Point(39,21),4326),'approximate','fixture',false),
 ('30000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000001','location',ST_SetSRID(ST_Point(40,22),4326),'exact','fixture',true);
DO $$ DECLARE t knowledge.temporal_extent; BEGIN
 SELECT * INTO t FROM knowledge.temporal_extent;
 IF knowledge.temporal_match(t,450,450)<>'possible' OR knowledge.temporal_match(t,550,550)<>'certain' OR knowledge.temporal_match(t,700,700)<>'none' THEN RAISE EXCEPTION 'temporal parity'; END IF;
 BEGIN UPDATE knowledge.temporal_extent SET start_low=700,start_high=750; RAISE EXCEPTION 'inverted period accepted'; EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN INSERT INTO knowledge.geometry_attestation(id,version_id,role,geom,precision_label,derivation) VALUES(gen_random_uuid(),t.version_id,'location',ST_SetSRID(ST_Point(181,21),4326),'exact','fixture'); RAISE EXCEPTION 'invalid coordinate accepted'; EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN INSERT INTO knowledge.geometry_attestation(id,version_id,role,geom,precision_label,derivation) VALUES(gen_random_uuid(),t.version_id,'location',ST_GeomFromText('POLYGON((0 0,2 2,2 0,0 2,0 0))',4326),'exact','fixture'); RAISE EXCEPTION 'invalid topology accepted'; EXCEPTION WHEN check_violation THEN NULL; END;
 IF (SELECT count(*) FROM knowledge.review_task WHERE version_id=t.version_id AND resolved_at IS NULL)<>2 THEN RAISE EXCEPTION 'missing internal tasks'; END IF;
 END $$;
SET LOCAL ROLE satac_publisher;
DO $$ BEGIN
 BEGIN PERFORM knowledge.publish('40000000-0000-0000-0000-000000000099',ARRAY['20000000-0000-0000-0000-000000000003']::uuid[]); RAISE EXCEPTION 'synthetic accepted'; EXCEPTION WHEN check_violation THEN NULL; END;
 END $$;
SELECT knowledge.publish('40000000-0000-0000-0000-000000000001',ARRAY['20000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002']::uuid[]);
RESET ROLE;
SET LOCAL ROLE satac_reader;
DO $$ DECLARE p jsonb; BEGIN
 SELECT payload INTO STRICT p FROM public_read.current_claims WHERE version_id='20000000-0000-0000-0000-000000000001';
 IF p ?| ARRAY['verification_status','epistemic_status','source_status','correction_status','restricted','synthetic','references'] OR jsonb_array_length(p->'geometries')<>1 THEN RAISE EXCEPTION 'public leak'; END IF;
 BEGIN PERFORM * FROM knowledge.review_task; RAISE EXCEPTION 'reader has private access'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN PERFORM knowledge.publish(gen_random_uuid(),ARRAY[]::uuid[]); RAISE EXCEPTION 'reader can publish'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 END $$;
RESET ROLE;
INSERT INTO knowledge.claim_version(id,claim_id,supersedes_id,subject_id,predicate,object_id)
VALUES('20000000-0000-0000-0000-000000000004','10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000001','BORN_IN','00000000-0000-0000-0000-000000000003');
SET LOCAL ROLE satac_publisher;
DO $$ BEGIN
 BEGIN PERFORM knowledge.correct('20000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000004','40000000-0000-0000-0000-000000000001','fixture','rule','test'); RAISE EXCEPTION 'duplicate release accepted'; EXCEPTION WHEN unique_violation THEN NULL; END;
 END $$;
SELECT knowledge.correct('20000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000004','40000000-0000-0000-0000-000000000002','fixture correction','fixture rule','test');
RESET ROLE;
DO $$ BEGIN
 IF (SELECT count(*) FROM knowledge.correction)<>1 OR (SELECT count(*) FROM knowledge.release)<>2 OR (SELECT count(*) FROM public_read.current_claims)<>2 THEN RAISE EXCEPTION 'correction audit/current release'; END IF;
 IF EXISTS(SELECT 1 FROM public_read.release_claims WHERE version_id='20000000-0000-0000-0000-000000000001') THEN RAISE EXCEPTION 'incorrect old version visible'; END IF;
 IF NOT EXISTS(SELECT 1 FROM knowledge.release_member WHERE release_id='40000000-0000-0000-0000-000000000001' AND version_id='20000000-0000-0000-0000-000000000001') THEN RAISE EXCEPTION 'snapshot lost'; END IF;
 BEGIN DELETE FROM knowledge.release_member; RAISE EXCEPTION 'mutable release'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END;
 END $$;
SET LOCAL ROLE satac_curator;
SELECT knowledge.flag_incorrect('20000000-0000-0000-0000-000000000002','fixture unknown correction','test');
RESET ROLE;
DO $$ BEGIN
 IF (SELECT count(*) FROM public_read.current_claims)<>1 OR NOT EXISTS(SELECT 1 FROM knowledge.review_task WHERE version_id='20000000-0000-0000-0000-000000000002' AND reason='correction' AND resolved_at IS NULL) THEN RAISE EXCEPTION 'unknown correction'; END IF;
 END $$;
ROLLBACK;
SELECT 'PASS: PostGIS schema, temporal/spatial checks, unsourced publication, permissions, correction, rollback and suppression' AS result;
