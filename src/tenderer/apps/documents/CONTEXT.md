# src/tenderer/apps/documents/: CONTEXT

What the client receives (`docs/architecture.md` §6.6). Built in M6 (2026-09-25) on the owner's instruction, before the concierge time logs that decide its "Keep if" line (`docs/build-plan.md` M6).

| File | Contains / does |
|---|---|
| `api.py` | `render_plan(bid)` returns subject, plain-text fallback and HTML of the client plan, from recorded data only: tender title and version, open deadlines (`alerts.api.open_deadlines`), the bid's checklist and go/no-go snapshots (cost lines and warnings in the sector pack's `labels`), and the draft declarations. A draft is rendered for each checklist requirement that has `tenders/<id>/declarations/<requirement>.txt`; ids must match `[A-Za-z0-9_-]+`, so nothing outside `tenders/` is read. `send_plan(bid)` e-mails it (HTML with a text fallback); every e-mail carries the never-ask line (X7). Greek number formats `_eur` and `_pct`. |
| (audit) | Sending a plan writes `plan.sent` (client data leaving the system) and a preview writes `plan.viewed`. |
| `models.py` | `ClientPlan`: proxy of `engagements.Bid`, only so the admin has a screen for plans. No tables. |
| `admin.py` | "Preview the client plan" (one bid, shown as the client will see it) and "E-mail the client plan to the client"; a failed send is shown to the operator with its exception class. |
| `apps.py` | Django app config (label `documents`). |

`templates/documents/`: the HTML template. `migrations/`: the proxy model's migration.

The watermark "ΠΡΟΣΧΕΔΙΟ – ελέγξτε πριν υπογράψετε" frames every draft. Only declarations without sensitive parts are drafted (R9 for the current tender); declarations about exclusion grounds or offences (R17, R21) are never drafted, and the client writes and signs every declaration in gov.gr.
