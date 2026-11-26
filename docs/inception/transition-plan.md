# P0 → P1 transition plan | خطة الانتقال

Status: proposed for owner review, 2026-11-26. Based on the v1.1 inception direction. This is not an accepted ADR, a release, or a closure report.

## Baseline and constraints

Legacy v0.13 is a functional exploratory atlas, not a completed P1. The public repository starts with documentation only. Preserve the original archives separately; import only after provenance and rights checks. No license is selected here.

## P0 — decisions and inventory

- [ ] Inventory v0.2–v0.13 and verify source/build manifests; choose a reproducible legacy baseline.
- [ ] Inventory code/data/asset licenses, attribution and redistribution terms; quarantine unknown rights.
- [ ] Review entity, predicate, evidence, geometry, temporal and release schemas; record ADRs (evidence-first, PostGIS, bitemporality, versioned read models, Arabic-first, no runtime LLM).
- [ ] Define timeline semantics: astronomical year zero vs historical display, BCE, BP/cal BP, unknown vs open bounds, possible vs certain overlap.
- [ ] Owner review of charter, contracts, rights register and ADRs before P0 closure.

## P1 — first vertical slice (after P0 review)

- [ ] Create locked dependencies, Compose, CI, env example, migrations and unit/integration/E2E tests.
- [ ] Implement PostgreSQL/PostGIS tables for entities, claims, time, geometry, sources, source versions, evidence, reviews and releases.
- [ ] Implement temporal/spatial validation, release-scoped read API and authenticated staging/review boundaries.
- [ ] Build Arabic RTL map, timeline, search, entity and evidence panels with accessible interactions.
- [ ] Isolate synthetic test fixtures; admit a small real sample only after documented rights and review.
- [ ] Validate legacy regression expectations against versioned dataset manifests; preserve invariants independently of record counts.
- [ ] Run and record acceptance evidence A01–A14 from the inception plan, explicitly marking unrun or out-of-scope checks.
- [ ] Publish a closure report and release manifest for owner review. If real licensed data is unavailable, mark that gate BLOCKED, not passed.

## Non-goals

No bulk publication of legacy datasets, no P2 expansion, no autonomous research-agent publication, no microservices, no new thematic layer as a substitute for the core.

## Proposed workflow

main is the stable integration branch. Work on focused branches, review via PRs, record decisions in docs/adr, and avoid merging unverified changes. Branch protection and CI are not yet configured. The proposed next implementation step is P0 schema/rights contracts and legacy inventory, not a claim of production readiness.
