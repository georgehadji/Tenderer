# src/tenderer/sectors/: CONTEXT

One package per sector (AD13, `docs/architecture.md` §6.12). A pack imports only the standard library and `core`; never Django, adapters or another pack. Written only when a real tender needs it (`docs/build-plan.md` §7).

| Folder | Sector |
|---|---|
| `taxi_student_transport/` | Taxi (Ε.Δ.Χ.) student transport; see its `CONTEXT.md` |
