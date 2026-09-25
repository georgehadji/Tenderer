# src/tenderer/shell/: CONTEXT

Django project and wiring (`docs/architecture.md` §6.10). Thin: no business decisions here. Built in M0 (2026-09-24).

| File | Contains / does |
|---|---|
| `settings.py` | Installs `tenderer.apps.engagements` and `tenderer.apps.alerts`; e-mail over SMTP with TLS (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DJANGO_DEFAULT_FROM_EMAIL` required); `ALERTS_HEARTBEAT_URL` for the dead man's switch; `TENDERER_PACKS` names the registry apps use. 12-factor settings: `DJANGO_SECRET_KEY` (required), `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `PG*` for PostgreSQL (TLS required by default). Production-safe defaults (HSTS, secure cookies, SSL redirect behind the proxy, `X_FRAME_OPTIONS=DENY`); `check --deploy` passes in CI. `Europe/Athens`, stored in UTC. |
| `urls.py` | Admin only, reachable through the identity-aware proxy (§9). |
| `wsgi.py` | WSGI entry point. |
| `packs.py` | `PACKS`: the registry of sector and jurisdiction packs, offer shapes and the lifecycle templates of `core/lifecycle`; `calendar(cc)` loads `reference/<cc>/holidays-*.csv`. The only module that imports packs. |
