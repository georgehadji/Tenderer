#!/usr/bin/env bash
# Monthly restore drill (docs/architecture.md §9, §13): dump the database, restore the dump into a throwaway
# PostgreSQL 17, and compare the row count of every table. "A backup that was never restored is not trusted."
# Usage: PGHOST=... PGPORT=... PGUSER=... PGPASSWORD=... PGDATABASE=... deploy/restore_drill.sh
# DRILL_NETWORK: Docker network that reaches PGHOST (default: host). Record the printed result in the audit log.
set -euo pipefail
: "${PGHOST:?}" "${PGDATABASE:?}" "${PGUSER:?}"
NET="${DRILL_NETWORK:-host}"
TARGET="tenderer-restore-drill-$$"
DUMP="$(mktemp -d)/drill.dump"
cleanup() { docker rm -f "$TARGET" >/dev/null 2>&1 || true; rm -f "$DUMP"; }
trap cleanup EXIT

tables_sql="SELECT string_agg(format('SELECT %L, count(*) FROM %I.%I', table_name, table_schema, table_name), ' UNION ALL ') FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
source_pg() { docker run --rm -i --network "$NET" -e PGHOST -e PGPORT -e PGUSER -e PGPASSWORD -e PGDATABASE \
  -e PGSSLMODE postgres:17 "$@"; }
target_pg() { docker exec -i -e PGUSER=drill -e PGDATABASE=drill "$TARGET" "$@"; }
counts() { local q; q=$("$@" psql -At -c "$tables_sql"); "$@" psql -At -F ' ' -c "$q ORDER BY 1"; }

echo "== dump $PGDATABASE on $PGHOST"
source_pg pg_dump --format=custom --no-owner --no-privileges > "$DUMP"
echo "dump: $(wc -c < "$DUMP") bytes"

echo "== restore into a throwaway PostgreSQL 17"
docker run -d --name "$TARGET" -e POSTGRES_DB=drill -e POSTGRES_USER=drill -e POSTGRES_PASSWORD=drill postgres:17 >/dev/null
until docker exec "$TARGET" pg_isready -U drill -d drill >/dev/null 2>&1; do sleep 1; done
sleep 2
target_pg pg_restore --exit-on-error --no-owner --no-privileges -d drill < "$DUMP"

source_counts=$(counts source_pg)
restored_counts=$(counts target_pg)
if [ -z "$source_counts" ] || [ "$source_counts" != "$restored_counts" ]; then
  diff <(echo "$source_counts") <(echo "$restored_counts") || true
  echo "RESTORE DRILL FAILED: row counts differ or no tables"; exit 1
fi
echo "$restored_counts" | awk '{ rows += $2 } END { printf "tables: %d, rows: %d\n", NR, rows }'
echo "RESTORE DRILL OK $(date -u +%Y-%m-%dT%H:%M:%SZ)"
