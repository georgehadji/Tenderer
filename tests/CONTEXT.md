# tests/: CONTEXT

pytest, with Hypothesis for properties. One file per module. Golden values come from outside the code under test: the tender, the v0 workbook check, or an independent Decimal oracle (`docs/build-plan.md` §7).

| File | Tests |
|---|---|
| `conftest.py` | `tender` fixture: the real tender loaded with the real pack registry. |
| `test_catalog.py` | The tender loads; version; determinism; every invalid row or field refuses the tender with its line and column. |
| `test_rules.py` | The document-freshness boundaries of the v0 workbook check (R1, R9, R12, R13, R18, R22, manual, not applicable); H3 property (no SATISFIED without its facts); deadlines (working days, roll-forward, ambiguity); every rule kind; `days360_us`. |
| `test_pricing.py` | Offer price rounding, guarantee amounts, validator errors in workbook order, groups, duplicates, floats rejected, participation-guarantee checks; property: prices are whole cents. |
| `test_taxi_costs.py` | Six routes × 100 discounts against the Decimal oracle of the workbook check; break-even including the edge route; missing inputs; warnings. |
| `test_gr.py` | Easter vectors 2026–2028, `reference/gr/` files equal the computation, number words. |
