# Canonical resolution candidate

Migration 0021 models a reviewed alias-to-canonical link as an ordinary release member with predicate CANONICAL_IDENTITY. Its private decision ID is immutable and is not projected publicly. A curator explicitly stages the direction from the latest same_entity decision; a source version and locator are required, with supporting evidence. Staging is idempotent and does not publish. Existing UUIDs, claims, crosswalks and historical manifests are never rewritten.

The publisher may explicitly include a staged link. Only disjoint pairs are supported in a release (no cycles, chains, multi-member clusters or transitive inference). A new decision for the pair withdraws the previous decision's link, including archives; it does not automatically publish a replacement. Source access revocation hides the link from the common public projection, not merely the citation. Private decision history and reasons are never projected. Ordinary claims and entity names remain independent. Archived manifests still verify.

This is reversible reference linking, not physical entity consolidation or partitioning of claims. Publication must select the eligible link explicitly. No real identity assertions or matches have been applied. Future group consistency, authenticated curator interface, and evidence reconciliation remain open. Tests and CI verification pending.
