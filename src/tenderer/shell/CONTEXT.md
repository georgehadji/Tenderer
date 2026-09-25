# src/tenderer/shell/: CONTEXT

Django project and wiring (`docs/architecture.md` §6.10). Thin: no business decisions here. Built in M0 (2026-09-24). Dependencies added in M7 and M8: `django-otp` (second factor for the admin, maintained by the Django community; writing TOTP ourselves would be more code to get wrong), `gunicorn` (WSGI server of the image), `whitenoise` (the admin's static files from the one container, no second web server).

| File | Contains / does |
|---|---|
| `settings.py` | Installs the apps (`audit` last, so its roles see every permission), `django_otp` with TOTP and static (break-glass) devices, whitenoise for the admin's static files, and the middleware chain: security headers, OTP verification, correlation ids. `TENDERER_COMMIT` (set at image build) goes into every `Tender.version`; `TENDERER_RETENTION_MONTHS` (unset until the lawyer sets N) gates `purge_expired`; `TENDERER_TENDERS_DIR` points at `tenders/`; e-mail over SMTP with TLS (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DJANGO_DEFAULT_FROM_EMAIL` required); `ALERTS_HEARTBEAT_URL` for the dead man's switch; `TENDERER_PACKS` names the registry apps use. 12-factor settings: `DJANGO_SECRET_KEY` (required), `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `PG*` for PostgreSQL (TLS required by default). Production-safe defaults (HSTS, secure cookies, SSL redirect behind the proxy, `X_FRAME_OPTIONS=DENY`); `check --deploy` passes in CI. `Europe/Athens`, stored in UTC. |
| `urls.py` | Admin only, reachable through the identity-aware proxy (§9). The admin site is `OTPAdminSite`: a password alone does not open it; a verified second factor does. |
| `logs.py` | `RedactPersonalData`, the filter on every log handler (`LOGGING` in `settings.py`): ΑΦΜ-like numbers, phone numbers and e-mail addresses become `[tax-id]`, `[phone]`, `[email]`, also inside tracebacks (§10.3). |
| `middleware.py` | `SecurityHeadersMiddleware`: Content-Security-Policy (scripts from our origin only, no inline script; inline styles allowed for the admin and the dashboard signal) and Permissions-Policy. |
| `wsgi.py` | WSGI entry point. |
| `packs.py` | `PACKS`: the registry of sector and jurisdiction packs, offer shapes and the lifecycle templates of `core/lifecycle`; `calendar(cc)` loads `reference/<cc>/holidays-*.csv`. The only module that imports packs. |
