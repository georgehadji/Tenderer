# src/tenderer/sectors/taxi_student_transport/: CONTEXT

Sector pack for taxi (Ε.Δ.Χ.) student transport. First used by `tenders/pkm-meth-student-transport-dsa-2026/`. Built in M3 (2026-09-24).

| File | Contains / does |
|---|---|
| `__init__.py` | `PACK`: resource kinds `vehicle`, `driver`, `escort` as JSON Schemas (the minimum fields of `docs/architecture.md` §8; `x-personal` marks personal fields, `x-unique` the uniqueness keys), the sector's document types, and `LABELS` (Greek text of each cost line and warning code). `apps/engagements` validates stored attributes against these schemas on every save. The escort keeps only `certificate_valid_until`, the expiry of the medical certificate (AD5). |
| `costs.py` | Go/no-go cost model of `docs/plan.md` §5, identical to the v0 workbook: per-day lines (fuel, wear, escort, insurance, opportunity cost, guarantee bank costs) and price shares (deductions from the jurisdiction pack, performance-guarantee carry). `analyse()` returns `GoNoGo` or `Missing` (never zero for a missing input); `fuel_scenario_net()`; `warnings()` always includes the fuel (§6.6.4) and cancellation (§7.6.1) risks. `gonogo()` is the registry hook: plain values (numbers as strings, dates, booleans) in, `GoNoGo` or `Missing` and the warnings out; floats and non-dates are refused. |
