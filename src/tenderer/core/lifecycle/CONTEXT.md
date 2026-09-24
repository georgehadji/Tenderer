# src/tenderer/core/lifecycle/: CONTEXT

Procedure types as data (`docs/architecture.md` §6.14, AD16). Pure; 100% branch coverage is a CI gate. Built in M4 (2026-09-24).

| File | Contains / does |
|---|---|
| `machine.py` | `Machine` (transition table `state -> event -> Transition(target, guard ids)`, plus events allowed from every non-final state), `Template` (engagement machine + bid machine), `fire(machine, state, event, context) -> Moved | Refused`. Guards are named by id in `GUARDS` and read only recorded results (`GuardContext`); an unknown guard id or target state fails when the template is built. |
| `templates.py` | `dps` (ONBOARDING → REGISTERED → APPLIED → ADMITTED → CONTRACTED → CLOSED; REJECTED; WITHDRAWN from any open state) and `open` (PREPARING → SUBMITTED → AWARDED/NOT_AWARDED → CONTRACTED → CLOSED). Both share the bid machine: DRAFT → CHECKED (guards `offer_valid`, `gonogo_recorded`, `offer_stage_clear`; H7) → CLIENT_SUBMITTED → AWARDED/NOT_AWARDED, `reopen` back to DRAFT, ABANDONED. `framework`, `negotiated` and `direct_award` wait for their first real tender. |
