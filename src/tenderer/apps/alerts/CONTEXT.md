# src/tenderer/apps/alerts/: CONTEXT

Reminders that must not fail silently (`docs/architecture.md` §6.5, AD11, H1, S5). Built in M5 (2026-09-25).

| File | Contains / does |
|---|---|
| `models.py` | `Deadline` (engagement, step, `due_on` = the conservative `remind_by` of `core/rules`, `legal_latest`, `ambiguous`, source `§`, acknowledged, closed), `UpcomingDeadline` (proxy model: the 14-day dashboard), `Outbox` (one e-mail each; unique `idempotency_key` `deadline-<id>-<kind>`; kinds `calendar`, `T-7`, `T-3`, `T-1`; attempts and the class name of the last error, never its text). Uses `TenantModel` from `engagements.models`, the one shared base class. |
| `api.py` | The only way in. `add_deadline` saves a deadline with its outbox rows in one transaction (transactional outbox): the calendar e-mail at once, and the T-7/T-3/T-1 reminders at 09:00 Athens time that are still ahead. `send_due` locks, sends and marks each due row in one transaction (at least once; the Message-ID is the idempotency key); `backlog` counts rows unsent for more than 30 minutes; `signal` is red when a send failed, the date passed, or the client has not acknowledged by T-3 (the operator phones); `render` builds subject and body: tender, step, date, source, and the line that we never ask for ΕΣΗΔΗΣ or Taxisnet codes (X7). |
| `ics.py` | Pure RFC 5545 calendar file for one all-day deadline, with alarms at 09:00 three days and one day before; TEXT escaping and 75-octet folding that never splits a UTF-8 character. |
| `admin.py` | Deadline screens (a new deadline goes through `api.add_deadline`; a saved one is read-only: close it and add a new one), actions "Client acknowledged" and "Close", the 14-day dashboard with a RED/AMBER/GREEN column, and a read-only outbox. |
| `apps.py` | Django app config (label `alerts`). |

`management/commands/`: the jobs cron runs. `migrations/`: generated schema migrations.

**Deploy (not verifiable in code):** cron every 5 minutes runs `manage.py send_outbox; manage.py heartbeat`; `ALERTS_HEARTBEAT_URL` is the ping URL of an external monitor with a 5-minute period, whose missed ping pages the operator; the sending domain publishes SPF, DKIM and DMARC `p=reject`. The alert drill (stop cron, confirm the page arrives) is recorded at go-live (M8).
