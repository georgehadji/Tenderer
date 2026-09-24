# .github/workflows/: CONTEXT

| File | Contains / does |
|---|---|
| `ci.yml` | The M0 gates on every push to `main` and every pull request: a PostgreSQL 17 service, `uv sync --locked`, CONTEXT coverage, `makemigrations --check`, ruff (with security rules), `mypy --strict` on core and packs, import-linter contracts, pytest with branch coverage (100% on `core/rules` and `core/lifecycle`), `pip-audit` of the runtime lockfile, `manage.py check --deploy` with production settings. Actions pinned by commit SHA; read-only token. |
