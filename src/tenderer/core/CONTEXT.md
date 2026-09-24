# src/tenderer/core/: CONTEXT

Pure modules: standard library only, no Django, no HTTP, no database, no clock (the date is a parameter). `mypy --strict` and the import contracts in `pyproject.toml` enforce this.

| Folder | Module | Spec |
|---|---|---|
| `catalog/` | Tender manifests and requirements as typed, immutable data; pack contracts and registry | `docs/architecture.md` §6.1, §6.12–§6.13 |
| `rules/` | Checklist evaluator, deadlines, calendar arithmetic | §6.2 |
| `pricing/` | Money, offer shapes and validator, guarantees, go/no-go | §6.3 |
| `lifecycle/` | Procedure templates as transition tables, one pure evaluator with guards | §6.14 |
