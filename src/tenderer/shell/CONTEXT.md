# src/tenderer/shell/: CONTEXT

Django project and wiring (`docs/architecture.md` §6.10). Thin: no business decisions here. Built in M0 (2026-09-24).

| File | Contains / does |
|---|---|
| `settings.py` | 12-factor settings: `DJANGO_SECRET_KEY` (required), `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `PG*` for PostgreSQL (TLS required by default). Production-safe defaults (HSTS, secure cookies, SSL redirect behind the proxy, `X_FRAME_OPTIONS=DENY`); `check --deploy` passes in CI. `Europe/Athens`, stored in UTC. |
| `urls.py` | Admin only, reachable through the identity-aware proxy (§9). |
| `wsgi.py` | WSGI entry point. |
| `packs.py` | `PACKS`: the registry of sector and jurisdiction packs, offer shapes and (until M4, by name only) lifecycle templates; `calendar(cc)` loads `reference/<cc>/holidays-*.csv`. The only module that imports packs. |
