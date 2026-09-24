# reference/gr/: CONTEXT

Greek public holidays per year, read by `core/rules` through `shell/packs.py` (`docs/architecture.md` §6.2). Columns: `date,name,reviewed`.

| File | Contains / does |
|---|---|
| `holidays-2026.csv` | 2026, generated from `jurisdictions/gr` on 2026-09-24. `reviewed=no` |
| `holidays-2027.csv` | 2027, same. Labour Day (1 May) falls on Holy Saturday: record whatever the government decides. `reviewed=no` |
| `holidays-2028.csv` | 2028, same. `reviewed=no` |
| `holidays-2029.csv` | 2029, same. `reviewed=no` |

**Review:** compare each file with the official list for its year (moved holidays, public-sector days such as Whit Monday), fix any row, then set `reviewed=yes` on every row. Until a year is reviewed, every working-day deadline in it is marked `ambiguous` and reminders go by the earliest date (AD8). A test fails when a file differs from the computation, so a deliberate difference (a moved holiday) must change that test too.
