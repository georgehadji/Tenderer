# src/tenderer/apps/engagements/: CONTEXT

Records about clients and their resources, and the lifecycle of each client × tender engagement and each bid (`docs/architecture.md` §6.4, §8). Built in M4 (2026-09-24).

| File | Contains / does |
|---|---|
| `models.py` | `Client` (tax ID and phone normalised by the jurisdiction pack's validators), `Resource` (kind and JSONB attributes validated by the sector pack's JSON Schema on every save; uniqueness keys from `x-unique`), `DocumentRecord` (metadata only; database CHECK `valid_until ≥ issued_on`), `Engagement` (with the tender title, shown to the client in reminders), `Bid` (recorded offer check, go/no-go and offer-stage checklist that feed the guard), `Acknowledgement` (fixed kinds, no free text). Every model carries `tenant_id` and calls `full_clean()` on save. Unknown states are refused by database CHECKs. Dependency `jsonschema`: the validator of the pack schemas (AD15); writing our own would be more code to get wrong. |
| `api.py` | The only way to change state: `open_engagement`, `fire_engagement`, `open_bid`, `fire_bid` (ask the transition table, raise `TransitionRefused`), `record_offer_check`, `record_gonogo`, `record_checklist` (a new record on a CHECKED bid sends it back to DRAFT). Audit events are added here in M7. |
| `admin.py` | Operator screens. Client shown as name + last three ΑΦΜ digits everywhere (H6). States are read-only; each event is an admin action that calls `api`. |
| `apps.py` | Django app config (label `engagements`). |

`migrations/`: generated schema migrations; CI fails if the models and migrations disagree.
