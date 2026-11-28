-- Disposable transaction only.
BEGIN;
DO $$ BEGIN
 IF public_read.asset_allowed('/physical/labels.json') IS DISTINCT FROM true
 OR public_read.asset_allowed('/legacy-art/dam.svg') IS DISTINCT FROM true
 OR public_read.asset_allowed('/land.geojson') IS DISTINCT FROM true
 OR public_read.asset_allowed('/assets/app.js') IS DISTINCT FROM false
 OR public_read.asset_allowed(NULL) IS DISTINCT FROM false
 THEN RAISE EXCEPTION 'asset path contract failed'; END IF;
 PERFORM knowledge.revoke_asset('/physical/labels.json','fixture','fixture');
 PERFORM knowledge.revoke_asset('/physical/labels.json','duplicate fixture','fixture');
 IF public_read.asset_allowed('/physical/labels.json') OR public_read.asset_allowed('/physical/manifest.json')
 OR NOT public_read.asset_allowed('/physical/relief/0/0/0.webp')
 OR (SELECT count(*) FROM knowledge.asset_revocation WHERE path='/physical/labels.json')<>1
 THEN RAISE EXCEPTION 'asset withholding failed'; END IF;
 IF has_table_privilege('satac_reader','knowledge.asset_revocation','SELECT')
 OR has_function_privilege('satac_reader','knowledge.revoke_asset(text,text,text)','EXECUTE')
 OR NOT has_function_privilege('satac_reader','public_read.asset_allowed(text)','EXECUTE')
 THEN RAISE EXCEPTION 'asset role contract failed'; END IF;
END $$;
ROLLBACK;
SELECT 'PASS: explicit static asset withholding, manifest masking and reader role isolation';
