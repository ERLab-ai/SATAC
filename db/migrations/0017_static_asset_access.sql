-- A07: static data and art access decisions.
BEGIN;
CREATE FUNCTION knowledge.valid_asset_path(p text) RETURNS boolean
 LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT coalesce(length(p)<=240 AND (p='/land.geojson' OR
 p ~ '^/(physical|legacy-art)/([A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+[.][A-Za-z0-9]+$'),false)
 $$;
CREATE TABLE knowledge.asset_revocation (
 path text PRIMARY KEY CHECK(knowledge.valid_asset_path(path)),
 reason text NOT NULL CHECK(btrim(reason)<>''), actor text NOT NULL CHECK(btrim(actor)<>''),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TRIGGER immutable_asset_revocation BEFORE UPDATE OR DELETE ON knowledge.asset_revocation
 FOR EACH ROW EXECUTE FUNCTION knowledge.immutable_row();
CREATE FUNCTION knowledge.revoke_asset(p text,reason_text text,actor_text text) RETURNS void
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,knowledge AS $$
 BEGIN
 PERFORM pg_advisory_xact_lock(716032);
 IF NOT knowledge.valid_asset_path(p) OR nullif(btrim(reason_text),'') IS NULL OR nullif(btrim(actor_text),'') IS NULL
 THEN RAISE EXCEPTION 'invalid asset revocation' USING ERRCODE='23514'; END IF;
 INSERT INTO knowledge.asset_revocation(path,reason,actor) VALUES(p,reason_text,actor_text) ON CONFLICT DO NOTHING;
 END $$;
-- Return a boolean only; the audit stays private.
CREATE FUNCTION public_read.asset_allowed(p text) RETURNS boolean
 LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,knowledge AS $$
 SELECT knowledge.valid_asset_path(p) AND NOT EXISTS (
 SELECT 1 FROM knowledge.asset_revocation x WHERE x.path=p
 OR (p='/physical/manifest.json' AND x.path LIKE '/physical/%'))
 $$;
REVOKE ALL ON FUNCTION knowledge.valid_asset_path(text),knowledge.revoke_asset(text,text,text),public_read.asset_allowed(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION knowledge.revoke_asset(text,text,text) TO satac_curator;
GRANT SELECT ON knowledge.asset_revocation TO satac_curator;
GRANT EXECUTE ON FUNCTION public_read.asset_allowed(text) TO satac_reader;
COMMIT;
