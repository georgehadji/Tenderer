# src/tenderer/apps/privacy/: CONTEXT

Data-subject requests and retention (GDPR Art. 15, 17, 5(1)(e); `docs/architecture.md` §6.4, §10.8). Built in M7 (2026-09-25). Sits above `engagements` and `alerts` because an erasure touches both.

| File | Contains / does |
|---|---|
| `api.py` | `export(client)`: every record of one client as a dict. `erase(client, reason)`: deletes queued e-mails, deadlines, acknowledgements, bids, engagements, document metadata, resources and the client in one transaction; refuses (`StillOpen`) while an engagement is not in a final state. `purge_expired(today)`: erases clients whose `retention_until` has passed and sets it N months ahead for clients whose engagements all ended; refuses to run until `TENDERER_RETENTION_MONTHS` is set (N is decided with the lawyer). Each action writes one audit event with ids and counts only. |
| `models.py` | `DataSubject`: proxy of `engagements.Client`, so the admin has a screen for these actions. No tables. |
| `admin.py` | For the admin role only (the actions need the delete permission): export as a JSON download, and erasure after a confirmation page. The generic "delete selected" action is removed, so nothing bypasses `erase`. |
| `apps.py` | Django app config (label `privacy`). |

`management/commands/`: the retention job. `migrations/`: the proxy model. `templates/privacy/`: the confirmation page.

Backups keep erased data until they rotate out (`docs/architecture.md` §9); the retention schedule has to state that window.
