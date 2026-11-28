# P0 domain contracts — proposal 0.2

Status: PROPOSED; not an accepted ADR or P1 implementation. Basis: inception v1.2 §§4–8, 11–12. The legacy v0.13.1 atlas is a separate regression baseline (PR #2). No historical facts are approved by these contracts.

## Identity and evidence
- Stable UUID entity IDs; external IDs are namespace-qualified assertions, never automatic merges. Entity types: Place, Person, Community, Polity, Event, Route, Institution, Work, Manuscript, Artifact, Concept. Sources, versions, claims, evidence, reviews and releases are separate records, not interchangeable domain entities.
- Each claim has exactly one subject, predicate and object (entity ID XOR typed value). Name/type/geometry and relations are claims; a new claim supersedes an old one without rewriting its published content. Preserve legacy IDs in a provenance crosswalk. Legacy records retain provenance and are not automatically labelled verified.
- SourceVersion identifies a source edition or snapshot, checksum and retrieval time; Evidence links claim, version, locator, stance and independence group. Review identifies reviewer, decision, rationale and transaction timestamp. Epistemic, publication, verification, source and correction states are independent. A structurally valid claim not known incorrect may be published without evidence or completed review; missing/incomplete sources and pending verification create internal tasks. Correct a known error directly when the correct value is known; audit previous/new values, basis, actor and timestamp and create a successor version. Never guess an unknown correction; suppress the known incorrect value. Exclude synthetic data, known incorrect values and records not selected for publication. Publication is transactional with immutable manifests and withdrawal history. These checks require database integration tests in P1.

## Time (executable reference: contracts/temporal.py)
- Inclusive integer astronomical years; 1 BCE = 0, 2 BCE = -1; public historical display has no year zero. No arbitrary historical epoch floor; database numeric/storage limits must be declared and tested in P1.
- Each endpoint has kind bounded (ordered inclusive low/high), open (explicit negative infinity for start, positive infinity for end), or unknown (not equivalent to open). Preserve original text, calendar, precision, dating units/reference and normalization method. BP/cal BP and AH normalization require source-specific conversion and uncertainty; this reference does not convert them. Never fabricate dates.
- A feasible world has start <= end. A query [q0,q1] overlaps iff start <= q1 and end >= q0. Return certain if all feasible worlds overlap, possible if some do, none otherwise; partially unknown endpoints conservatively cap at possible; two unknown endpoints are undated, excluded from dated queries. Open/open is explicitly all time, not unknown. Valid time is independent of transaction time and source time.

## Space
- WGS84 / EPSG:4326, longitude then latitude. Unknown geometry has no coordinates. Geometry attestation belongs to a claim, with role, precision, derivation, visibility and optional uncertainty radius in metres. Reject invalid topology and out-of-range coordinate values; use geodesic/geography or suitable projected CRS for metric calculations. Represent sovereignty, administration, influence, claim, trade and distribution independently; no inference of boundaries from control relations. Public geometry must honour visibility and release membership. PostGIS, antimeridian queries and geometry validation remain P1 tasks.

## Publication and API
- Public reads are release-scoped (release_id, claim_ids, stable pagination); no draft mode on public routes. Public outputs exclude internal status fields, review tasks and correction logs; include available references and genuine scientific uncertainty. Staging and reviews require authenticated curator scopes; AI writes only staging. Release manifest must cover the published membership and canonical content, with withdrawals handled explicitly. Contracts are proposed, not yet SQL or OpenAPI implementations.

## Interoperability
CIDOC CRM, Linked Places Format, WHG, EDTF and PROV-O are mapping targets per v1.1; no conformance claim. P1 must specify concrete mappings, SQL constraints, migration tests and Arabic-first read models.
