# Public claim export candidate — A07

GET /api/v1/export/claims?release=<uuid>&limit=25&after=<version-uuid> provides bounded JSON pages (1–50 claims). The release is mandatory; the cursor is the last version ID. Output is satac-public-claims-v1 and contains only the existing public claim projections. Deep astronomical year values retain the existing decimal-string encoding.

Exports are generated live by the same masked public_read.release_claims path used by individual claim reads, not from private snapshots or disk archives. Source, geometry, embedded-source, embedded-URL and whole-version decisions apply on every page. Responses inherit no-store headers. No audit reasons, administrative statuses, or static file bytes are included.

A multi-page export is release-pinned, not an access-policy snapshot: a later revocation can remove a record between pages. Copies previously downloaded by a reader cannot be recalled. There is no server-side persistent export artifact or bulk offline export. Actual distribution permissions remain the owner's responsibility. Acceptance requires SQL/HTTP regression results; no production release.
