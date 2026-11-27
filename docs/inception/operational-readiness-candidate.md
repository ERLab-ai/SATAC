# Operational readiness candidate (A01 / A11)

## Confirmed prerequisite
Security and accessibility exact-head run 46035802235 and PR run 46035812527 passed. Roadmap v1.2 A01 requires clean Compose + migrations, A11 core public operation independent of LLM/GPU. Localhost deployment rehearsal, not public Beta or production release.

## Run from a clean checkout
Build the web bundle using the locked CI recipe (physical asset generator and verifier, npm ci, npm run build), or obtain the verified dist artifact from the same commit. The web Docker image copies only dist; does not regenerate geography in runtime. Require Docker Engine with Compose v2, Linux x86_64 (tested dependency environment), disk for images/DB. Python and nginx base images use version tags, not digest pins.
Create private .satac-secrets (0700, outside shared folder), generate independent high-entropy passwords (at least 32 characters), chmod 0444 on files only so UID 10001 can read local Compose file mounts. Protect parent directory; do not commit secrets:
```sh
umask 077
mkdir -m 700 .satac-secrets
python -c 'import secrets; print(secrets.token_hex(32))' > .satac-secrets/admin_password
python -c 'import secrets; print(secrets.token_hex(32))' > .satac-secrets/reader_password
chmod 0444 .satac-secrets/*
docker compose up -d --build db migrate api web
curl -fsS http://127.0.0.1:8080/health
curl -i http://127.0.0.1:8080/ready
```
/health verifies dedicated reader connectivity; /ready returns 503 until active release. Startup applies numbered migrations under session advisory lock with atomic per-file SQL body+ledger checksum, refuses missing/changed history and existing untracked schema. All 13 original wrappers inspected before implementation. Re-run migrate to apply new migrations or rotate reader password; admin password rotation requires explicit DB operation (initialization secret does not alter existing role). Runtime API only has reader secret and app source; migration/staging service has admin secret, schema and source inputs, and exits. DB/API ports not published. Web listens on loopback; API/gateway nonroot read-only filesystem and reduced capabilities. DB volume persists across ordinary down. Nginx same-origin gateway limits request rate, connections and body size, protects HTTP headers, no-store and access logs without query strings. Limits per immediate peer IP, not public reverse-proxy-aware; no TLS/public binding, hosted service or external monitoring.

## Explicit initial release only
```sh
docker compose run --rm -T ops stage > proposal.json
sha256sum proposal.json
# Operator inspects exact membership and projection digest; no automatic publication.
docker compose run --rm -T ops publish-initial --manifest-sha256 APPROVED_FILE_SHA256 --release APPROVED_NEW_UUID < proposal.json
curl -fsS http://127.0.0.1:8080/ready
```
Imports nine existing stage-only importers, expected 3309 version IDs. Proposal sorted membership and projection digest; initial publisher verifies exact proposal file hash, membership, repeatable-read projection under publication lock, invokes authorized publisher role and verifies stored manifest. Rejects prior release, so cannot replace active membership or bypass corrections. Operator authorizes actual publication; CI release is disposable only. No synthetic or test fixtures in administration/runtime image. No independent source or distribution verification.

## Backup and restore
Use restricted storage, encryption and off-host copy for production. Example local backup:
```sh
umask 077
docker compose exec -T db pg_dump -U satac_admin -d satac -Fc > satac-backup.dump
sha256sum satac-backup.dump > satac-backup.dump.sha256
```
CI drill restores archive into separate DB in same disposable cluster with --exit-on-error, verifies ledger, membership, active release, manifest and reader visibility. pg_dump omits global roles, passwords, host secrets and static assets; same-cluster drill does not certify disaster recovery to new cluster. New cluster requires matching roles separately and restoration into empty DB, validation before switching. Do not use down -v outside disposable environment. RPO/RTO, scheduled off-host backups, alerts, log retention, secret rotation policy, TLS and public exposure require further acceptance.

## CI
Separate operational job after verified web build downloads only dist artifact, builds images, checks schema/startup, no release by default, migration rerun, identical staged proposals, rejected invalid approval, explicit disposable publication, rejected second initial release, HTTP data/counts/security, backup and restore. Unique Compose project, generated secrets and no production endpoints. CI pending. Vulnerability scans, hash-locked wheels, digest pins all images, comprehensive security/accessibility/visual acceptance and production deployment not complete.
