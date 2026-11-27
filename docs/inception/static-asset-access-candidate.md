# A07 — Static asset access candidate

Explicit owner-directed decisions for normalized paths under physical/, legacy-art/ and land.geojson. The Nginx gateway requests a read-only allow/deny decision before serving the file. The original physical manifest is withheld if any physical file is revoked. Original static bytes, hashes and release membership are unchanged. Audit reason and actor remain private. The protected static namespace is distinct from application JavaScript and CSS.

Operator command: docker compose run --rm ops revoke-asset --path /physical/labels.json --reason ... --actor ... (only after owner authorization). No decision has been applied to actual content.

Limitations: existing downloaded copies cannot be recalled. Copies distributed in container images, compiled JavaScript, duplicated or derived files, and separately served assets require independent inventory, rebuilding and removal. Vite development preview is not the access-enforcement gateway. A blocked map resource may degrade its layer. No licensing determination and no complete A07 acceptance until end-to-end tests pass.
