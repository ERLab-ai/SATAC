# P0 → P1 transition plan | خطة الانتقال

Status: proposed for owner review, 2026-11-26. Based on the v1.2 inception direction. This is not an accepted ADR, a release, or a closure report.

## Baseline and constraints

Legacy v0.13 is a functional exploratory atlas, not a completed P1. The legacy baseline and stabilization PR #2 exist separately. Preserve the original archives; record provenance and implement owner-configured access settings. Distribution decisions belong to the owner.

## P0 — decisions and inventory

- [ ] Inventory v0.2–v0.13 and verify source/build manifests; choose a reproducible legacy baseline.
- [ ] Inventory provenance and technical access metadata; implement owner-configured access rules.
- [ ] Review entity, predicate, evidence, geometry, temporal and release schemas; record ADRs (evidence-first, PostGIS, bitemporality, versioned read models, Arabic-first, no runtime LLM).
- [ ] Define timeline semantics: astronomical year zero vs historical display, BCE, BP/cal BP, unknown vs open bounds, possible vs certain overlap.
- [ ] Owner review of charter, contracts, source registry and owner access settings and ADRs before P0 closure.

## P1 — first vertical slice (after P0 review)

- [ ] Create locked dependencies, Compose, CI, env example, migrations and unit/integration/E2E tests.
- [ ] Implement PostgreSQL/PostGIS tables for entities, claims, time, geometry, sources, source versions, evidence, reviews and releases.
- [ ] Implement temporal/spatial validation, known-error correction with audit, independent publication/verification/source/correction states, internal review tasks, release-scoped public reads and authenticated staging/review boundaries.
- [ ] Build Arabic RTL map, timeline, search, entity and evidence panels with accessible interactions.
- [ ] Isolate synthetic test fixtures; admit a small real sample under owner-configured access settings; incomplete review or missing source alone is not a publication blocker.
- [ ] Validate legacy regression expectations against versioned dataset manifests; preserve invariants independently of record counts.
- [ ] Run and record acceptance evidence A01–A14 from the inception plan, explicitly marking unrun or out-of-scope checks.
- [ ] Publish a closure report and release manifest for owner review. If real data is unavailable, mark that gate BLOCKED, not passed.

## Non-goals

No bulk publication of legacy datasets, no P2 expansion, no autonomous research-agent publication, no microservices, no new thematic layer as a substitute for the core.

## Proposed workflow

main is the stable integration branch. Work on focused branches, review via PRs, record decisions in docs/adr, and avoid merging unverified changes. Legacy CI passed; foundation CI and branch protection remain separate tasks. The proposed next implementation step is P0 schema/publication contracts and legacy inventory, not a claim of production readiness.
