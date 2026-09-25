# src/tenderer/apps/privacy/management/commands/: CONTEXT

| File | Contains / does |
|---|---|
| `purge_expired.py` | Cron, daily: `manage.py purge_expired` runs `api.purge_expired` in its own correlation scope; exits non-zero while `TENDERER_RETENTION_MONTHS` is not set. |
