# src/tenderer/apps/alerts/management/commands/: CONTEXT

Jobs run by cron every 5 minutes, in this order: `manage.py send_outbox; manage.py heartbeat` (`docs/architecture.md` §6.5, AD11).

| File | Contains / does |
|---|---|
| `send_outbox.py` | Sends every due outbox row once (`api.send_due`); prints the counts; exits non-zero if any send failed (those rows are retried on the next run). |
| `heartbeat.py` | Dead man's switch: pings `ALERTS_HEARTBEAT_URL` (https only) when no notification has waited more than 30 minutes; otherwise exits non-zero without pinging, so the external monitor pages the operator. A stopped cron also stops the pings. |
