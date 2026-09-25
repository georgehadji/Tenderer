#!/usr/bin/env bash
# Smoke test of the production image against a throwaway PostgreSQL 17 (docs/architecture.md §9, H10).
# Usage: deploy/smoke.sh [image]   (default tenderer:local; build it first with `docker build -t tenderer:local .`)
set -euo pipefail
IMAGE="${1:-tenderer:local}"
NET="tenderer-smoke-$$"
PG="tenderer-smoke-db-$$"
WEB="tenderer-smoke-web-$$"
cleanup() { docker rm -f "$WEB" "$PG" >/dev/null 2>&1 || true; docker network rm "$NET" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker network create "$NET" >/dev/null
docker run -d --name "$PG" --network "$NET" -e POSTGRES_DB=tenderer -e POSTGRES_USER=migrator \
  -e POSTGRES_PASSWORD=smoke-only postgres:17 >/dev/null
until docker exec "$PG" pg_isready -U migrator -d tenderer >/dev/null 2>&1; do sleep 1; done
sleep 2

ENVS=(-e DJANGO_SECRET_KEY=smoke-test-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz
      -e DJANGO_ALLOWED_HOSTS=localhost -e DJANGO_DEFAULT_FROM_EMAIL=alerts@tenderer.example
      -e PGHOST="$PG" -e PGDATABASE=tenderer -e PGSSLMODE=disable)
run() { docker run --rm --network "$NET" "${ENVS[@]}" "$@"; }

echo "== migrate (as the owner role)"
run -e PGUSER=migrator -e PGPASSWORD=smoke-only "$IMAGE" python manage.py migrate --noinput | tail -1
echo "== app role and grants (deploy/roles.sql)"
docker exec -i "$PG" psql -q -v ON_ERROR_STOP=1 -U migrator -d tenderer \
  -c "CREATE ROLE tenderer_app LOGIN PASSWORD 'smoke-app'" < /dev/null
docker exec -i "$PG" psql -q -v ON_ERROR_STOP=1 -U migrator -d tenderer < deploy/roles.sql
APP=(-e PGUSER=tenderer_app -e PGPASSWORD=smoke-app)
echo "== check --deploy"
run "${APP[@]}" "$IMAGE" python manage.py check --deploy --fail-level WARNING
echo "== the app role cannot change the audit log"
if docker exec "$PG" psql -q -U tenderer_app -d tenderer -c "DELETE FROM audit_auditevent" 2>/dev/null; then
  echo "FAIL: tenderer_app could delete audit events"; exit 1
fi
echo "== jobs"
run "${APP[@]}" "$IMAGE" python manage.py send_outbox
if run "${APP[@]}" "$IMAGE" python manage.py purge_expired 2>/dev/null; then
  echo "FAIL: purge_expired ran without TENDERER_RETENTION_MONTHS"; exit 1
fi
run "${APP[@]}" -e TENDERER_RETENTION_MONTHS=24 "$IMAGE" python manage.py purge_expired
echo "== web"
docker run -d --name "$WEB" --network "$NET" "${ENVS[@]}" "${APP[@]}" "$IMAGE" >/dev/null
page=""
for _ in $(seq 1 30); do
  page=$(docker exec "$WEB" python -c "
import urllib.request
r = urllib.request.urlopen(urllib.request.Request('http://localhost:8000/admin/login/',
    headers={'X-Forwarded-Proto': 'https', 'Host': 'localhost'}))
print(r.status, bool(r.headers.get('X-Correlation-ID')), 'otp_token' in r.read().decode())" 2>/dev/null) && break
  sleep 1
done
echo "login page (status, correlation id, OTP field): $page"
[ "$page" = "200 True True" ] || { echo "FAIL: admin login page"; exit 1; }
css=$(docker exec "$WEB" python -c "
import urllib.request
r = urllib.request.urlopen(urllib.request.Request('http://localhost:8000/static/admin/css/base.css',
    headers={'X-Forwarded-Proto': 'https', 'Host': 'localhost'}))
print(r.status)")
[ "$css" = "200" ] || { echo "FAIL: static files"; exit 1; }
echo "== image contents"
if docker run --rm "$IMAGE" test -e /app/discovery; then echo "FAIL: discovery/ is in the image"; exit 1; fi
[ "$(docker run --rm "$IMAGE" id -u)" = "10001" ] || { echo "FAIL: image runs as root"; exit 1; }
echo "SMOKE OK"
