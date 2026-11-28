#!/usr/bin/env bash
# Disposable CI only: never run against an existing deployment/volume.
set -euo pipefail
test "${SATAC_OPERATIONAL_SMOKE:-}" = 1
export COMPOSE_PROJECT_NAME="satac_ops_ci_${GITHUB_RUN_ID:-local}_${GITHUB_RUN_ATTEMPT:-1}"
test "${GITHUB_ACTIONS:-}" = true
# Never reuse a previous CI project or its volume.
test -z "$(docker ps -aq --filter label=com.docker.compose.project=$COMPOSE_PROJECT_NAME)"
test -z "$(docker volume ls -q --filter label=com.docker.compose.project=$COMPOSE_PROJECT_NAME)"
export SATAC_SECRET_DIR="$(mktemp -d)"
export SATAC_PORT=18080
umask 077
work="$(mktemp -d)"
trap 'docker compose logs --tail=50 web api migrate >&2 || true; docker compose down -v --remove-orphans || true; rm -rf "$SATAC_SECRET_DIR" "$work"' EXIT
for name in admin_password reader_password; do
  python -c 'import secrets;print(secrets.token_hex(32))' > "$SATAC_SECRET_DIR/$name"
  chmod 0444 "$SATAC_SECRET_DIR/$name"
done
docker compose config -q
docker compose up -d --build db migrate api web
for _ in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:18080/health >/dev/null; then break; fi
  sleep 2
done
curl -fsS http://127.0.0.1:18080/health
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/ready)" = 503
curl -fsS http://127.0.0.1:18080/api/v1/releases | python -c 'import json,sys;assert json.load(sys.stdin)["releases"]==[]'
test "$(docker compose run --rm -T --no-deps migrate | tail -n1)" = '{"applied":21,"new":0}'
docker compose --profile tools build ops
docker compose run --rm -T --no-deps ops stage > "$work/proposal.json"
docker compose run --rm -T --no-deps ops stage > "$work/proposal-again.json"
cmp "$work/proposal.json" "$work/proposal-again.json"
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/ready)" = 503
hash="$(sha256sum "$work/proposal.json" | cut -d' ' -f1)"
release="dddd0000-0000-4000-8000-000000000001"
# Reject mismatched approval before explicit disposable publication.
if docker compose run --rm -T --no-deps ops publish-initial --manifest-sha256 invalid --release "$release" < "$work/proposal.json"; then exit 1; fi
docker compose run --rm -T --no-deps ops publish-initial --manifest-sha256 "$hash" --release "$release" < "$work/proposal.json"
curl -fsS http://127.0.0.1:18080/ready
curl -fsS http://127.0.0.1:18080/api/v1/articles | python -c 'import sys,json;assert len(json.load(sys.stdin)["articles"])==50'
curl -fsS http://127.0.0.1:18080/api/v1/cells | python -c 'import sys,json;assert len(json.load(sys.stdin)["cells"])==2480'
curl -fsS 'http://127.0.0.1:18080/api/v1/routes/path?start=MAKKA_398E213N_S_JAZI&end=MADINA_396E244N_S_JAZI' | python -c 'import sys,json;assert json.load(sys.stdin)["meters"]==392496'
curl -fsS http://127.0.0.1:18080/physical/manifest.json | python -c 'import sys,json;assert len(json.load(sys.stdin)["files"])==52'
curl -fsSI http://127.0.0.1:18080/ | grep -qi 'content-security-policy:'
curl -fsSI http://127.0.0.1:18080/assets/maplibre-gl-worker.mjs | grep -Ei '^content-type: (application|text)/javascript'
test "$(curl -s -X POST -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/api/v1/releases)" = 403
if docker compose run --rm -T --no-deps ops publish-initial --manifest-sha256 "$hash" --release "dddd0000-0000-4000-8000-000000000002" < "$work/proposal.json"; then exit 1; fi
# A07 disposable fixture: live gateway enforcement, without rewriting the asset.
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/physical/labels.json)" = 200
docker compose run --rm -T --no-deps ops revoke-asset --path /physical/labels.json --reason 'fixture withholding' --actor 'fixture curator'
for url in '/physical/labels.json' '/physical/labels.json?cache=1' '/physical/manifest.json'; do
  test "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:18080$url")" = 403
done
test "$(curl -sI -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/physical/labels.json)" = 403
test "$(curl -s -H 'Range: bytes=0-5' -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/physical/labels.json)" = 403
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/physical/relief/0/0/0.webp)" = 200
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/_asset_access)" = 404
# Internal identity and review CLI rehearsal using disposable unpublished records.
ea="eeee0000-0000-4000-8000-000000000001"
eb="eeee0000-0000-4000-8000-000000000002"
es="eeee0000-0000-4000-8000-000000000003"
ec="eeee0000-0000-4000-8000-000000000004"
ev="eeee0000-0000-4000-8000-000000000005"
docker compose exec -T db psql -U satac_admin -d satac -v ON_ERROR_STOP=1 <<SQL
INSERT INTO knowledge.entity VALUES('$ea','Place'),('$eb','Place');
INSERT INTO knowledge.source_version(id,title) VALUES('$es','Disposable identity source');
INSERT INTO knowledge.claim VALUES('$ec');
INSERT INTO knowledge.claim_version(id,claim_id,subject_id,predicate,object_text,language)
VALUES('$ev','$ec','$ea','NAME','Disposable review fixture','en');
SQL
assertion="$(docker compose run --rm -T --no-deps ops assert-external-identity --entity "$ea" --namespace fixture --external-id 42 --source "$es" --locator 'p. 1' --actor 'fixture curator' | python -c 'import sys,json;print(json.load(sys.stdin)["id"])')"
test "$assertion" = "$(docker compose run --rm -T --no-deps ops assert-external-identity --entity "$ea" --namespace fixture --external-id 42 --source "$es" --locator 'p. 1' --actor 'fixture curator' | python -c 'import sys,json;print(json.load(sys.stdin)["id"])')"
candidate="$(docker compose run --rm -T --no-deps ops propose-identity --entity-a "$ea" --entity-b "$eb" --reason 'fixture proposal' --actor 'fixture curator' | python -c 'import sys,json;print(json.load(sys.stdin)["id"])')"
decision="$(docker compose run --rm -T --no-deps ops decide-identity --candidate "$candidate" --decision same_entity --reason 'fixture comparison' --reviewer 'fixture curator' --source "$es" --locator 'p. 1' | python -c 'import sys,json;print(json.load(sys.stdin)["id"])')"
docker compose run --rm -T --no-deps ops decide-identity --candidate "$candidate" --expected "$decision" --decision undetermined --reason 'fixture reconsideration' --reviewer 'fixture curator'
review="$(docker compose run --rm -T --no-deps ops record-claim-review --version "$ev" --decision verified --reason 'fixture review' --reviewer 'fixture curator' | python -c 'import sys,json;print(json.load(sys.stdin)["id"])')"
docker compose run --rm -T --no-deps ops record-claim-review --version "$ev" --expected "$review" --decision disputed --reason 'fixture further review' --reviewer 'fixture curator'
test "$(docker compose exec -T db psql -U satac_admin -d satac -At -v ON_ERROR_STOP=1 -c "SELECT (SELECT count(*) FROM knowledge.identity_decision WHERE candidate_id='$candidate')=2 AND (SELECT verification_status FROM knowledge.claim_review_state WHERE version_id='$ev')='disputed' AND NOT EXISTS(SELECT 1 FROM public_read.release_claims WHERE version_id='$ev');")" = t
echo 'PASS: internal identity/review CLI, idempotent assertions, decision history and unpublished isolation'
# Backup/restore drill in separate database of disposable cluster.
docker compose exec -T db pg_dump -U satac_admin -d satac -Fc > "$work/backup.dump"
test -s "$work/backup.dump"
docker compose exec -T db createdb -U satac_admin satac_restore
docker compose exec -T db pg_restore -U satac_admin -d satac_restore --exit-on-error < "$work/backup.dump"
check="SELECT (SELECT count(*) FROM satac_ops.schema_migrations)=21 AND (SELECT count(*) FROM knowledge.release_member)=3309 AND knowledge.verify_release('$release') AND (SELECT release_id FROM knowledge.current_release)='$release';"
test "$(docker compose exec -T db psql -U satac_admin -d satac_restore -At -v ON_ERROR_STOP=1 -c "$check")" = t
test "$(docker compose exec -T db psql -U satac_admin -d satac_restore -At -v ON_ERROR_STOP=1 -c "SET ROLE satac_runtime; SELECT count(*) FROM public_read.release_claims;" | tail -n1)" = 3309
test "$(docker compose exec -T db psql -U satac_admin -d satac_restore -At -v ON_ERROR_STOP=1 -c "SET ROLE satac_runtime; SELECT NOT public_read.asset_allowed('/physical/labels.json') AND public_read.asset_allowed('/physical/relief/0/0/0.webp');" | tail -n1)" = t
test "$(docker compose exec -T db psql -U satac_admin -d satac_restore -At -v ON_ERROR_STOP=1 -c "SELECT (SELECT count(*) FROM knowledge.identity_decision WHERE candidate_id='$candidate')=2 AND (SELECT verification_status FROM knowledge.claim_review_state WHERE version_id='$ev')='disputed';")" = t
docker compose exec -T db dropdb -U satac_admin satac_restore
echo 'PASS: live asset withholding at gateway and restored access decisions'
echo 'PASS: isolated compose startup, migration ledger, stage idempotence, explicit release, gateway, backup and restore'
