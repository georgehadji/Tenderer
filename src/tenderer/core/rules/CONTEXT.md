# src/tenderer/core/rules/: CONTEXT

Checklists and deadlines (`docs/architecture.md` §6.2). Pure; 100% branch coverage is a CI gate. Built in M2 (2026-09-24).

| File | Contains / does |
|---|---|
| `checklist.py` | `evaluate(requirements, facts, key_dates) -> tuple[Item, ...]`: one small evaluator per validity kind, kept in a dict. Statuses `SATISFIED`, `NOT_SATISFIED`, `UNKNOWN` (a missing fact or date; shown like NOT_SATISFIED, AD7) and `NOT_APPLICABLE`. `DocumentFact` holds metadata only (AD5). Working-day freshness counts holidays as working days, which gives the shortest window (AD8), as the v0 workbook does. `open_items()` lists what still blocks. |
| `deadlines.py` | `deadline(event_on, rule, calendar) -> Deadline(remind_by, legal_latest, ambiguous, note)`: computes every counting convention and reminds by the earliest; a year without a reviewed calendar is `ambiguous`. `offer_validity_end()` from the tender's offer terms (§4.4.1). |
| `dates.py` | `add_months` (spreadsheet EDATE), `weekdays_back`, `days360_us` (YEARFRAC basis 0), `Calendar` and `load_calendar()` for `reference/<cc>/holidays-<year>.csv`. |
