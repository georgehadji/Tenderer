# OWASP ASVS 5.0 Level 2: self-review of v1

| | |
|---|---|
| Date | 2026-09-25 |
| Scope | The v1 code of this repository (M0–M8 of [`build-plan.md`](build-plan.md)), the production image ([`Dockerfile`](../Dockerfile)) and [`deploy/`](../deploy/CONTEXT.md). Not the host, which is chosen at go-live. |
| Method | Chapter by chapter against the code, with the test or script that shows each control. A self-review, not an external audit ([`architecture.md`](architecture.md) §12 v1 gate). |
| Limits | Chapter titles follow ASVS 5.0 as [`architecture.md`](architecture.md) §10.6 cites it (17 chapters, 30 May 2025). Requirement numbers are **not** cited: they were not checked against the published text in this session, so this review names controls, not IDs. |

**Surface in v1.** No public endpoint (AD6). One inbound path: the Django admin behind an identity-aware proxy. Outbound: e-mail to clients, a heartbeat ping. Clients never log in.

## Chapters

| Chapter | Applies | Control in v1 | Evidence | Gap before go-live |
|---|---|---|---|---|
| V1 Encoding and sanitization | Yes | Django templates escape every value; draft declarations are plain text shown escaped inside HTML; reminder e-mails are plain text; e-mail headers refuse newlines (Django) | `test_documents.py::test_values_are_escaped` (script tags, template syntax, `settings.SECRET_KEY` in values) | None |
| V2 Validation and business logic | Yes | Values are validated when they enter: ΑΦΜ check digit, plate, phone; resource attributes against the pack's JSON Schema on every save; database CHECKs on states and dates; floats refused for money; transitions only through the tables; DRAFT → CHECKED guard (H7) | `test_engagements.py`, `test_pricing.py`, `test_lifecycle.py`, `test_gr.py` | None |
| V3 Web frontend security | Yes (admin) | CSP with scripts from our origin only, `frame-ancestors 'none'`, X-Frame-Options DENY, nosniff, Referrer-Policy, Permissions-Policy; HSTS with preload; secure cookies | `shell/middleware.py`; `test_audit.py` checks the headers; `check --deploy` in CI | Inline styles stay allowed (admin and dashboard use style attributes) |
| V4 API and web service | No | No API in v1 | n/a | Review again in v4 (client portal) |
| V5 File handling | Partly | No uploads, no document files stored (AD5). The v0 import reads a local .xlsx the operator chooses: openpyxl on defusedxml, cell values only, whole import in one transaction; tender declaration files are read only from `tenders/<id>/` with ids restricted to `[A-Za-z0-9_-]` | `test_v0import.py` (unreadable file refused); `test_documents.py::test_unsafe_tender_id_drafts_nothing` | The import runs in the app process; the sandbox of §6.9 is for untrusted public files (v3), not for the operator's own workbook |
| V6 Authentication | Yes | Django password hashing and validators; a second factor is required for the admin (`OTPAdminSite`, TOTP; static codes for the sealed break-glass account); WebAuthn at the identity-aware proxy | `test_audit.py::test_the_admin_needs_a_second_factor` | WebAuthn inside the app is **not** built (§10.2 prefers it; TOTP is the fallback it allows). Choose and configure the proxy; enrol devices; seal the break-glass codes |
| V7 Session management | Yes | Server-side sessions; `Secure` and `HttpOnly` cookies; CSRF on every form; 8-hour session age | `settings.py`; `check --deploy` | An idle timeout shorter than 8 hours is not set; decide at go-live |
| V8 Authorization | Yes | Roles `operator`, `reviewer`, `admin` from permissions, synced after every migrate; erasure and export need the admin role; audit log read-only | `test_audit.py::test_roles_hold_the_permissions_of_the_design` | Assign roles to real accounts at go-live |
| V9 Self-contained tokens | No | No JWTs or similar | n/a | n/a |
| V10 OAuth and OIDC | Depends on the proxy | The app is not an OAuth client in v1 | n/a | If the proxy uses OIDC, review its configuration then |
| V11 Cryptography | Yes, at the edges | No custom cryptography. TLS to the database is required by default (`PGSSLMODE=require`); SMTP with STARTTLS; secret key from the environment | `settings.py` | Encryption at rest is the managed services' (§10.3) |
| V12 Secure communication | Yes | TLS terminates at the proxy; HSTS; SSL redirect; database TLS; e-mail TLS | `check --deploy` in CI and in `deploy/smoke.sh` | Certificate and TLS configuration of the proxy |
| V13 Configuration | Yes | 12-factor settings, secrets only from the environment, production is the default; image runs as a non-root user; base images pinned by digest; hash-pinned lockfile; `pip-audit` on every push; Actions pinned by SHA; the image excludes `discovery/` | CI (`ci.yml`); `deploy/smoke.sh` checks the user id and the image contents | Secret scanning with push protection: **unverified** that it is on for this repository |
| V14 Data protection | Yes | Minimum data (AD5), prohibited fields absent (schema review test), `tenant_id` everywhere, export and erasure, retention job, no personal data in audit details | `test_engagements.py::test_schema_review_no_field_for_prohibited_data`, `test_privacy.py` | Retention period N (lawyer); backup rotation window in the retention schedule |
| V15 Secure coding and architecture | Yes | Functional core without I/O, import contracts, `mypy --strict` on the core, ruff security rules, mutation testing of money and deadline code (978/1000) | `lint-imports`, `scripts/mutation.sh` | None |
| V16 Security logging and error handling | Yes | Append-only audit log (trigger + grants), correlation id per request and job, sign-in events without usernames, views and exports audited; failed jobs exit non-zero and a backlog withholds the heartbeat. Every log handler removes ΑΦΜ-like numbers, phone numbers and e-mail addresses, also from tracebacks | `test_audit.py`, `test_alerts.py`, `test_shell.py` | Error tracking with personal-data scrubbing (§10.5) is a host choice at go-live |
| V17 WebRTC | No | n/a | n/a | n/a |

## Open items (owner: operator, before the first real client in v1)

1. Identity-aware proxy with WebAuthn in front of the admin; TOTP devices enrolled; break-glass codes sealed.
2. Error tracking with personal-data scrubbing (§10.5).
3. Secret scanning with push protection confirmed on the repository.
4. Retention period N and the backup window in the retention schedule ([`gdpr-v1.md`](gdpr-v1.md)).
