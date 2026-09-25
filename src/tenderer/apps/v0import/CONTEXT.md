# src/tenderer/apps/v0import/: CONTEXT

Imports a filled copy of the v0 workbook (`discovery/concierge-phase-b-workbook.xlsx`) into v1 and reconciles every number (build-plan M8, flow F1). Built on 2026-09-25. The workbook stays the operator's entry sheet for invitations, route tables, client costs and offers; this module records them in v1 and recomputes everything with v1's code.

| File | Contains / does |
|---|---|
| `api.py` | `import_workbook(path, client, tender)`: reads the cached values of the four sheets (never formulas; openpyxl on defusedxml), opens or reuses the engagement and the bid, records go/no-go per route (through the sector pack's `gonogo` hook), the offer check, the offer-stage checklist and document metadata (resources are matched by label), and queues the submission and award-documents deadlines. Each v1 result is compared with the workbook's: net per day at 0%, the largest discount without loss, the participation guarantee per route, every offer price and error, the guarantee check, every document status. R11 is derived from the offer check and R8 from the guarantee, as in the workbook. Any difference rolls the whole import back (`Differences`, with the report) unless accepted. Re-importing the same file changes nothing. |
| `apps.py` | Django app config (label `v0import`). No models. |

`management/commands/`: the operator's command. Dependencies: `openpyxl` (the standard reader of .xlsx) with `defusedxml` installed, so the XML is parsed with the hardened parser (`docs/architecture.md` §6.9).
