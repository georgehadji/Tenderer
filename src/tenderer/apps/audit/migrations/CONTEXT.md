# src/tenderer/apps/audit/migrations/: CONTEXT

CI runs `makemigrations --check`.

| File | Contains / does |
|---|---|
| `0001_initial.py` | Generated: table `audit_auditevent`. |
| `0002_append_only.py` | Written by hand (Django has no trigger operation): a `BEFORE UPDATE OR DELETE` trigger that raises on every row, whoever asks. TRUNCATE is refused to the app role by `deploy/roles.sql` instead, so test databases can still be flushed. |
