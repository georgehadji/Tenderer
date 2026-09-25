# src/tenderer/apps/audit/: CONTEXT

Append-only record of who did what and when, and the access model (`docs/architecture.md` §6.7, §10.2, H8). Built in M7 (2026-09-25). Every other app writes through `api.record`; nothing here imports another app.

| File | Contains / does |
|---|---|
| `models.py` | `AuditEvent`: `at`, `tenant_id`, `actor_id` (user id, never a name), `action`, `object_ref` (`app.model:pk`), `details` (ids and codes only), `correlation_id`. `save()` of an existing row and `delete()` raise; the database refuses them too (migration 0002, `deploy/roles.sql`). |
| `api.py` | `record(action, target, details)`, `ref(obj)`, and `correlated(actor_id)`: the scope of one request or job, whose correlation id and actor every event inside it carries. |
| `middleware.py` | `CorrelationMiddleware`: one correlation id per request (after authentication, so the actor is known), returned as `X-Correlation-ID`. |
| `admin.py` | `AuditedAdmin`: the base of every admin screen that shows client data; opening a record writes `viewed`, a list writes `listed`. Read-only view of the audit log (admin and reviewer roles). |
| `apps.py` | Roles `operator` (view, add, change on engagements, alerts, documents), `reviewer` (view, incl. the audit log), `admin` (everything incl. users, second-factor devices, data-subject actions), kept in sync after every `migrate`; sign-in, sign-out and failed sign-in events (no username stored for a failure). Listed last in `INSTALLED_APPS`. |

`migrations/`: the table, and the trigger that makes it append-only.

Events written today: `engagement.opened`, `engagement.transition`, `bid.opened`, `bid.transition`, `bid.recorded`, `deadline.added`, `deadline.acknowledged`, `deadline.closed`, `notification.sent`, `notification.failed`, `plan.viewed`, `plan.sent`, `client.exported`, `client.erased`, `client.retention_set`, `v0.imported`, `viewed`, `listed`, `auth.signed_in`, `auth.signed_out`, `auth.sign_in_failed`.
