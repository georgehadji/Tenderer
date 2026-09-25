# deploy/: CONTEXT

Operations files for the production image of `Dockerfile` (`docs/architecture.md` §9). Tested on 2026-09-25 against PostgreSQL 17 containers.

| File | Contains / does |
|---|---|
| `roles.sql` | Run as the table owner after every `migrate`: the app role `tenderer_app` gets DML on every table, but only INSERT and SELECT on `audit_auditevent` (§10.2). |
| `smoke.sh` | `deploy/smoke.sh [image]`: against a throwaway PostgreSQL 17, migrates as the owner, applies `roles.sql`, runs `check --deploy` as the app role, confirms the app role cannot delete audit events, runs the jobs (and that `purge_expired` refuses without a retention period), serves the admin login page with its second-factor field, correlation id and static files, and checks the image holds no `discovery/` and does not run as root. CI runs it on every push. |
| `restore_drill.sh` | Monthly restore drill: `pg_dump` of the database, restore into a throwaway PostgreSQL 17, row counts of every table compared. Prints `RESTORE DRILL OK <time>`; record it in the audit log (§13). |

Not in this folder, because they depend on the host chosen at go-live: the scheduler entries (`send_outbox; heartbeat` every 5 minutes, `purge_expired` daily), the external heartbeat monitor, the identity-aware proxy, the EU e-mail provider with SPF, DKIM and DMARC `p=reject`, backups with point-in-time recovery.
