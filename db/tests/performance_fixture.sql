-- A13 isolated benchmark only. Never use this fixture to publish knowledge.
-- Requires a disposable clone, named satac_benchmark, of the CI database.
BEGIN;
DO $$ BEGIN
 IF current_database()<>'satac_benchmark' OR current_setting('satac.benchmark_only',true) IS DISTINCT FROM 'on' THEN
   RAISE EXCEPTION 'benchmark fixture requires isolated database and explicit test flag';
 END IF;
END $$;
CREATE TEMP TABLE benchmark_rows ON COMMIT DROP AS
 SELECT i, md5('satac-perf-claim:'||i)::uuid AS c,
 md5('satac-perf-version:'||i)::uuid AS v,
 (34+(i%100)*0.25)::numeric AS lon,
 (12+(i/100)*0.22)::numeric AS lat,
 100+(i%10)*100 AS yr
 FROM generate_series(0,9999) AS i;
INSERT INTO knowledge.entity VALUES
 ('eeee0000-0000-4000-8000-000000000001','Person'),
 ('eeee0000-0000-4000-8000-000000000002','Place');
INSERT INTO knowledge.claim SELECT c FROM benchmark_rows;
INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_id,synthetic)
 SELECT v,c,'eeee0000-0000-4000-8000-000000000001','LIVED_IN','eeee0000-0000-4000-8000-000000000002',true
 FROM benchmark_rows;
-- The production publisher must still reject every synthetic version.
DO $$ DECLARE v uuid; BEGIN
 SELECT b.v INTO v FROM benchmark_rows b LIMIT 1;
 BEGIN
 PERFORM knowledge.publish(gen_random_uuid(),ARRAY[v]);
 RAISE EXCEPTION 'synthetic version unexpectedly publishable';
 EXCEPTION WHEN check_violation THEN NULL;
 END;
END $$;
-- Build the read-path fixture directly, not through the production publisher.
-- The benchmark release is never made current, never imported elsewhere, and
-- the isolated database is dropped after measurement. Geometry/temporal shape
-- matches the normal immutable payload, with explicitly synthetic content.
CREATE TEMP TABLE benchmark_payloads ON COMMIT DROP AS
 SELECT v, jsonb_build_object(
 'claim_id',c,'version_id',v,'subject_id','eeee0000-0000-4000-8000-000000000001',
 'predicate','LIVED_IN','object_id','eeee0000-0000-4000-8000-000000000002',
 'scientific_note','SYNTHETIC BENCHMARK ONLY',
 'temporal',jsonb_build_object('start_kind','bounded','start_low',yr,'start_high',yr,
 'end_kind','bounded','end_low',yr+99,'end_high',yr+99,'original_text','synthetic',
 'calendar','CE','precision_label','year','normalization_method','benchmark'),
 'geometries',jsonb_build_array(jsonb_build_object('role','location','precision','synthetic',
 'geometry',jsonb_build_object('type','Point','coordinates',jsonb_build_array(lon,lat))))
 ) AS payload FROM benchmark_rows;
INSERT INTO knowledge.release(id,manifest_sha256)
 SELECT 'eeee0000-0000-4000-8000-000000000003',
 encode(public.digest(convert_to(jsonb_agg(payload ORDER BY v)::text,'UTF8'),'sha256'),'hex')
 FROM benchmark_payloads;
INSERT INTO knowledge.release_member
 SELECT 'eeee0000-0000-4000-8000-000000000003',v,payload FROM benchmark_payloads;
DO $$ BEGIN
 IF (SELECT count(*) FROM knowledge.release_member WHERE release_id='eeee0000-0000-4000-8000-000000000003')<>10000
 OR knowledge.verify_release('eeee0000-0000-4000-8000-000000000003') IS DISTINCT FROM true
 OR EXISTS(SELECT 1 FROM knowledge.current_release WHERE release_id='eeee0000-0000-4000-8000-000000000003')
 THEN RAISE EXCEPTION 'invalid benchmark isolation or fixture'; END IF;
END $$;
COMMIT;
ANALYZE knowledge.release_member;
ANALYZE knowledge.claim_version;
SELECT 'PASS: isolated synthetic 10000-claim read fixture; publisher rejects synthetic versions';
