# A05 persistent integration candidate

Adds migration 0015, version-scoped group metadata and a release-scoped read API with Arabic evidence panel. Existing claim versions and release manifests remain unchanged. Only explicit, same-subject and same-predicate groups; first slice supports NAME and relation claims, not structured legacy editorial payloads. An editor must establish scientific incompatibility and temporal scope before assignment; different values alone do not establish conflict. Old versions cannot be updated, and groups are immutable.

The endpoint derives groups exclusively from masked release snapshots and requires at least two visible alternatives. References and geometries inherit the existing withdrawal/revocation overlay. Group and alternative cursors require a pinned release; public metadata contains no administrative state. Group listing paginates, and alternatives are paginated independently at 50 items. The Arabic panel shows distinct values, original time, scientific notes and available evidence without automatic ranking; geometry uses inspectable GeoJSON in this candidate, not a comparison map.

Integration test evidence is pending. No new historical claims, publication or phase closure.
