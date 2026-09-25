# src/tenderer/apps/: CONTEXT

Django applications (`docs/architecture.md` §5.1). They import `core` and reach packs only through the registry named by `settings.TENDERER_PACKS` (an import-linter contract forbids importing a pack). Other modules call an app only through its `api.py`.

| Folder | Module |
|---|---|
| `engagements/` | Clients, resources, document metadata, engagements and bids; see its `CONTEXT.md` |
| `alerts/` | Deadlines, the reminder outbox, the jobs that send it and the heartbeat, the 14-day dashboard; see its `CONTEXT.md` |
