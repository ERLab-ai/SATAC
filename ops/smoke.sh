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
test "$(docker compose run --rm -T --no-deps migrate | tail -n1)" = '{"applied":14,"new":0}'
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
test "$(curl -s -X POST -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/api/v1/releases)" = 403
if docker compose run --rm -T --no-deps ops publish-initial --manifest-sha256 "$hash" --release "dddd0000-0000-4000-8000-000000000002" < "$work/proposal.json"; then exit 1; fi
# Backup/restore drill in separate database of disposable cluster.
docker compose exec -T db pg_dump -U satac_admin -d satac -Fc > "$work/backup.dump"
test -s "$work/backup.dump"
docker compose exec -T db createdb -U satac_admin satac_restore
docker compose exec -T db pg_restore -U satac_admin -d satac_restore --exit-on-error < "$work/backup.dump"
check="SELECT (SELECT count(*) FROM satac_ops.schema_migrations)=14 AND (SELECT count(*) FROM knowledge.release_member)=3309 AND knowledge.verify_release('$release') AND (SELECT release_id FROM knowledge.current_release)='$release';"
test "$(docker compose exec -T db psql -U satac_admin -d satac_restore -At -v ON_ERROR_STOP=1 -c "$check")" = t
test "$(docker compose exec -T db psql -U satac_admin -d satac_restore -At -v ON_ERROR_STOP=1 -c "SET ROLE satac_runtime; SELECT count(*) FROM public_read.release_claims;" | tail -n1)" = 3309
docker compose exec -T db dropdb -U satac_admin satac_restore
echo 'PASS: isolated compose startup, migration ledger, stage idempotence, explicit release, gateway, backup and restore'
