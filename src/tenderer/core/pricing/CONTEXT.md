# src/tenderer/core/pricing/: CONTEXT

Money, offer shapes, offer validator, guarantees, go/no-go (`docs/architecture.md` §6.3, AD9, AD17). Pure. Never proposes a discount (`CLAUDE.md` §5). Built in M3 (2026-09-24).

| File | Contains / does |
|---|---|
| `money.py` | `Money` (Decimal + ISO 4217 code; floats raise `TypeError`), `to_decimal()` (the only way numbers enter pricing), `round_cents` (half up), `ceil_cents`. |
| `offer.py` | Offer shape `discount_on_reference`, the only entry in `OFFER_SHAPES` until a tender needs another: `offer_price()`, `guarantee_amount()` (rounded up to the cent), `validate_offer()` returning the first `LineError` per line in the v0 workbook's order, `check_participation_guarantee()`. Errors are codes; the Greek wording belongs to the documents module. |
| `gonogo.py` | `go_no_go(reference, costs, paid_days_per_year) -> GoNoGo`: net per day for every integer discount 0–99, per year, and the break-even discount (`None` when there is a loss at 0%). `Costs` keeps every line (explainable computation). Sector packs supply the cost lines. |

Golden tests: `tests/test_pricing.py`, `tests/test_taxi_costs.py` (the Decimal oracle that checked the v0 workbook).
