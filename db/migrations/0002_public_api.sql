-- Public metadata and temporal matching over immutable public snapshots.
BEGIN;
CREATE VIEW public_read.releases WITH (security_barrier=true) AS
 SELECT r.id AS release_id,r.created_at,r.manifest_sha256 AS snapshot_sha256,
 EXISTS(SELECT 1 FROM knowledge.current_release c WHERE c.release_id=r.id) AS is_current
 FROM knowledge.release r;
GRANT SELECT ON public_read.releases TO satac_reader;
CREATE FUNCTION public_read.temporal_match(p jsonb,qlo numeric,qhi numeric)
 RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,knowledge AS $$
 SELECT CASE WHEN p IS NULL OR p='null'::jsonb THEN 'undated'
 ELSE knowledge.temporal_match(jsonb_populate_record(NULL::knowledge.temporal_extent,p),qlo,qhi) END $$;
REVOKE ALL ON FUNCTION public_read.temporal_match(jsonb,numeric,numeric) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public_read.temporal_match(jsonb,numeric,numeric) TO satac_reader;
COMMIT;
