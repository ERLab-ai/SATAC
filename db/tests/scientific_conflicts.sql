-- A05 invariant tests. All invented records stay inside a rollback transaction.
BEGIN;
DO $$
DECLARE p uuid:=gen_random_uuid(); q uuid:=gen_random_uuid(); a uuid:=gen_random_uuid(); b uuid:=gen_random_uuid();
 c1 uuid:=gen_random_uuid(); c2 uuid:=gen_random_uuid(); c3 uuid:=gen_random_uuid(); c4 uuid:=gen_random_uuid();
 v1 uuid:=gen_random_uuid(); v2 uuid:=gen_random_uuid(); v3 uuid:=gen_random_uuid(); v4 uuid:=gen_random_uuid();
 g uuid:=gen_random_uuid(); s uuid:=gen_random_uuid(); r1 uuid:=gen_random_uuid(); r2 uuid:=gen_random_uuid(); h text;
BEGIN
 INSERT INTO knowledge.entity VALUES(p,'Person'),(q,'Person'),(a,'Place'),(b,'Place');
 INSERT INTO knowledge.claim VALUES(c1),(c2),(c3),(c4);
 INSERT INTO knowledge.scientific_conflict_group VALUES(g,p,'BORN_IN');
 INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_id,conflict_group_id)
 VALUES(v1,c1,p,'BORN_IN',a,g),(v2,c2,p,'BORN_IN',b,g);
 INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_id) VALUES(v3,c3,p,'BORN_IN',a);
 BEGIN
 INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_id,conflict_group_id)
 VALUES(v4,c4,q,'BORN_IN',a,g);
 RAISE EXCEPTION 'mixed-subject conflict accepted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 BEGIN
 INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_id,conflict_group_id)
 VALUES(v4,c4,p,'LIVED_IN',a,g);
 RAISE EXCEPTION 'mixed-predicate conflict accepted';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 BEGIN UPDATE knowledge.claim_version SET conflict_group_id=g WHERE id=v3;
 RAISE EXCEPTION 'version mutated'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END;
 BEGIN UPDATE knowledge.scientific_conflict_group SET subject_id=q WHERE id=g;
 RAISE EXCEPTION 'group mutated'; EXCEPTION WHEN object_not_in_prerequisite_state THEN NULL; END;
 INSERT INTO knowledge.source_version(id,title) VALUES(s,'A05 SQL fixture source');
 INSERT INTO knowledge.evidence(id,version_id,source_version_id,locator,stance) VALUES(gen_random_uuid(),v1,s,'p. 1','supports');
 h:=knowledge.publish(r1,ARRAY[v1,v2,v3]);
 IF (SELECT count(*) FROM public_read.release_claims WHERE release_id=r1 AND payload->>'conflict_group_id'=g::text)<>2
 OR (SELECT payload FROM public_read.release_claims WHERE release_id=r1 AND version_id=v2) ? 'references'
 OR (SELECT payload FROM public_read.release_claims WHERE release_id=r1 AND version_id=v3) ? 'conflict_group_id'
 THEN RAISE EXCEPTION 'conflict projection failed'; END IF;
 IF NOT EXISTS(SELECT 1 FROM knowledge.review_task WHERE version_id=v2 AND reason='documentation')
 THEN RAISE EXCEPTION 'missing internal followup'; END IF;
 IF knowledge.publish(r2,ARRAY[v1,v2,v3]) IS DISTINCT FROM h THEN RAISE EXCEPTION 'manifest not repeatable'; END IF;
 PERFORM knowledge.revoke_source(s,'test revocation','fixture');
 PERFORM knowledge.withhold_version(v2,'test withholding','fixture');
 IF EXISTS(SELECT 1 FROM public_read.release_claims WHERE release_id=r1 AND version_id=v2)
 OR (SELECT payload FROM public_read.release_claims WHERE release_id=r1 AND version_id=v1) ? 'references'
 OR knowledge.verify_release(r1) IS DISTINCT FROM true THEN RAISE EXCEPTION 'revocation or manifest failed'; END IF;
END $$;
DO $$ BEGIN
 IF has_table_privilege('satac_reader','knowledge.scientific_conflict_group','SELECT')
 OR has_table_privilege('satac_reader','knowledge.scientific_conflict_group','INSERT')
 THEN RAISE EXCEPTION 'private conflict table privilege leak'; END IF;
END $$;
ROLLBACK;
SELECT 'PASS: explicit immutable A05 scope, snapshot stability, missing-source policy, withdrawal and reader isolation';
