# A05 — Scientific conflict reference contract (candidate)

Implementation increment after verified MapLibre recovery (CI run 46046215988). Not an A05 acceptance pass.

- Explicit conflict group identifier attached to a claim version, chosen in staging; never inferred merely from shared subject/predicate, different name, temporal overlap, missing source or administrative verification status.
- A group means incompatible alternatives within a single subject and predicate; an editor must establish the comparable question/time/context before grouping. The reference checks subject and predicate only; full temporal and semantic comparison is a later integration task.
- Public conflict read is derived from the same release's visible claim projections. At least two visible alternatives are required. Keep stable claim/version IDs and each available source locator and scientific note. No ranking or selection. Missing evidence creates internal follow-up under owner policy v1.2, not a public warning or a publication blocker.
- Withdrawals take effect in archived public reads; immutable release manifests do not change. Group changes on published claims require successor versions, not retroactive edits. Correction is not a scientific disagreement; correct known errors via the existing audited mechanism.
- Reference tests use invented fixtures in memory only; no historical source or record is introduced.

Remaining implementation: PostgreSQL version metadata/projection and SQL checks, release-scoped API with source/geometry revocation overlay, Arabic RTL panel linking each alternative to evidence, isolated DB/HTTP/browser tests (including withdrawal, rollback, pagination, and no admin leakage). Do not display a group solely because it has a single surviving alternative. Review group identity and revision handling before deploying the migration. Do not mark A05 complete until the end-to-end acceptance test passes.
