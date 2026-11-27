# SATAC — P0 contract review candidate

Independent foundation track, not a P1 release. The owner-directed [knowledge publication and correction policy v1.2](docs/editorial/knowledge-publication-policy-v1.2-ar.md) supersedes conflicting source/review publication gates. [Revised inception v1.2](docs/SATAC_Inception_Strategy_Architecture_Roadmap_v1.2_AR.md). See [domain contracts](docs/inception/domain-contract.md), [proposed ADRs](docs/adr/ADR-001-to-009.md), [legacy inventory](docs/inception/legacy-inventory.md), and [predicate registry](ontology/predicates.json). Run the dependency-free reference checks using `python -m unittest discover -s tests -v` (Python 3.13.5 tested). The legacy app remains in its own branch. Owner review is required before closing P0 or beginning production P1.

Executable P0 reference: [publication and correction contract](docs/inception/publication-reference.md). Foundation CI runs the temporal and publication reference tests. Database candidate: [persistent knowledge core](docs/inception/database-candidate.md). [Public API candidate](docs/inception/api-candidate.md) — read-only, no production deployment.

[Entity names and Arabic search candidate](docs/inception/entity-search-candidate.md): three-place legacy sample, stage-only importer and release-scoped search.

[Web atlas candidate](docs/inception/web-atlas-candidate.md): Arabic React/MapLibre interface, read-only API, actual sample and browser integration.

[Legacy visual and feature parity register](docs/inception/atlas-parity.md): owner-approved product direction, incremental recovery; not replacement release.
