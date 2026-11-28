# Internal identity and review operations

Run only via the trusted administrative Compose profile on an authorized deployment. These are not public HTTP routes.

- assert-external-identity --entity UUID --namespace NAMESPACE --external-id ID --source UUID [--locator TEXT] --actor ACTOR
- propose-identity --entity-a UUID --entity-b UUID --reason TEXT --actor ACTOR
- decide-identity --candidate UUID [--expected UUID] --decision same_entity|distinct_entities|undetermined --reason TEXT --reviewer REVIEWER [--source UUID] [--locator TEXT]
- record-claim-review --version UUID [--expected UUID] --decision verified|review_required|disputed|known_incorrect --reason TEXT --reviewer REVIEWER

Use docker compose run --rm ops followed by the command. Each invocation runs under the curator database role, returns a JSON operation and UUID, and never merges entities or publishes a release. Omit expected only for the first decision; subsequent decisions must cite the previous event UUID. Positive identity matches need a source and locator. A known error review suppresses the claim using the existing correction policy. The CLI is trusted-operator attribution, not individual reviewer authentication.

The operational smoke test creates disposable unpublished fixtures, exercises the CLI, checks idempotence/history/isolation, and verifies the review and identity history survives backup/restore. No real identities or reviews are created by this development change; verification remains pending.
