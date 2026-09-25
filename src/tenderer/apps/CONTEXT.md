# src/tenderer/apps/: CONTEXT

Django applications (`docs/architecture.md` §5.1). They import `core` and reach packs only through the registry named by `settings.TENDERER_PACKS` (an import-linter contract forbids importing a pack). Other modules call an app only through its `api.py`.

| Folder | Module |
|---|---|
| `engagements/` | Clients, resources, document metadata, engagements and bids; see its `CONTEXT.md` |
| `documents/` | The client plan: checklist, deadlines, go/no-go and draft declarations as one HTML e-mail; see its `CONTEXT.md` |
| `audit/` | Append-only audit log, correlation ids, roles, sign-in events; see its `CONTEXT.md` |
| `privacy/` | Data-subject export and erasure, the retention job; see its `CONTEXT.md` |
| `v0import/` | Import and reconciliation of v0 workbook copies; see its `CONTEXT.md` |
| `alerts/` | Deadlines, the reminder outbox, the jobs that send it and the heartbeat, the 14-day dashboard; see its `CONTEXT.md` |
