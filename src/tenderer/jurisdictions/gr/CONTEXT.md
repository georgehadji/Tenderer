# src/tenderer/jurisdictions/gr/: CONTEXT

Greece. Built in M2–M3 (2026-09-24).

| File | Contains / does |
|---|---|
| `__init__.py` | `PACK`: national document types; `orthodox_easter()` (Meeus Julian + 13 days, valid 1900–2099) and `public_holidays(year)` (fixed days, Clean Monday, Good Friday, Easter Monday, Whit Monday); `PAYMENT_DEDUCTION_RATE` = 0.12% × (1 + 3% stamp duty × 1.2 for ΟΓΑ) = 0.0012432 (§6.6.2); `number_in_words()` for 0–99, because the offer template wants the discount written out. Moved holidays are not predictable, so the reviewed files in `reference/gr/` win. ΑΦΜ and plate validators arrive with M4. |
