# src/tenderer/: CONTEXT

The application package. Layout and dependency rules: [`docs/architecture.md`](../../docs/architecture.md) §5.2–§5.4; build order: [`docs/build-plan.md`](../../docs/build-plan.md). A folder exists only once its module is built.

| Folder | Layer | Contains |
|---|---|---|
| `core/` | pure core | tender catalog, rules (checklists, deadlines), pricing: `core/CONTEXT.md` |
| `sectors/` | packs | one package per sector: `sectors/CONTEXT.md` |
| `jurisdictions/` | packs | one package per country: `jurisdictions/CONTEXT.md` |
| `shell/` | imperative shell | Django project, pack registry: `shell/CONTEXT.md` |

`py.typed` marks the package as typed. Import direction: `shell` → packs → `core`, checked by `lint-imports` (contracts in `pyproject.toml`).
