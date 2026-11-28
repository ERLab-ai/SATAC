# Canonical identity read and staging operations

GET /api/v1/entities/{entity_id}/canonical?release=<uuid> returns the requested UUID, its canonical UUID and the public link claim (including evidence) or a null link. It is a lookup, not a redirect: existing entity detail and search keep original identifiers. The explicit release is mandatory. Without a link, an entity must have a visible name in that release. The link itself is suppressed by withdrawal or loss of its supporting source; resolution never falls back to private staging.

The curator may use docker compose run --rm ops stage-identity-link --decision UUID --alias UUID --canonical UUID. This stages a version only. A separate publisher action must select it. If a source is revoked, the link is hidden immediately and cannot be carried forward in a new publication; the publisher must omit it from the selected membership. A superseding identity decision withdraws the old link, including archives. Archived manifest hashes are unchanged. There is no general release-authoring CLI in this increment; existing SQL publisher and initial publication workflow are unchanged.

SQL and HTTP regressions test disjoint pairs, stable UUIDs, unpublished isolation, explicit release, evidence, archive separation, rollback, export and private metadata isolation. Verification pending.
