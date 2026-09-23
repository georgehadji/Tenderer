# discovery/: CONTEXT

Customer discovery for the gates in [`docs/plan.md`](../docs/plan.md) §6: step 2 (interviews) and step 3 (concierge Phase A). The repo is public, so personal data never enters git: raw interview notes, filled checklists and time logs, and the key from codes to people live in `discovery/private/`, which `.gitignore` excludes (it is not part of the repo and has no CONTEXT file), or in an EU spreadsheet workspace. Only aggregated summaries are committed.

| File | Contains / does |
|---|---|
| `interviews-taxi-2026.md` | Step 2 interview kit (Greek): how the gate is measured (§1), who and how many (§2), recruitment channels with public contacts and outreach rules under Law 3471/2006 art. 11 and GDPR (§3), invitation message (§4), oral consent script (§5), interview guide for taxi owners and accountants (§6), after-interview routine and data handling (§7), log columns (§8), summary and decision rules (§9), sources. |
| `interview-log-template.csv` | Header-only template for the interview log (22 columns, described in `interviews-taxi-2026.md` §8). Copy it to `discovery/private/` before use; never commit a filled copy. |
| `concierge-phase-a-2026.md` | Step 3 concierge kit (Greek): one-off setup before the first meeting (§1), rules for every meeting incl. no credentials and the ΕΕΕΣ filled only in the client's account (§2), meeting plan mapped to `sop.md` Phase A (§3), what is recorded and what never (§4, per `architecture.md` AD5), the two templates' columns (§5), gate measurement and what may be committed (§6), GDPR Art. 30 record of processing for steps 2 and 3 (§7), sources. |
| `concierge-checklist-template.csv` | Template of the per-client Phase A checklist, metadata only: R1, R2, R5–R7 (per vehicle), `ack:exclusion_grounds`, R3, R4, `milestone:accepted`, each with a three-valued status and dates. Columns in `concierge-phase-a-2026.md` §5. |
| `concierge-time-log-template.csv` | Header-only template for the time log: minutes per step and blocker codes, the basis for gate X. Columns in `concierge-phase-a-2026.md` §5. |
| `pilot-agreement-draft.md` | Draft pilot agreement with the GDPR Art. 13 privacy notice (Greek): scope, what we never do, client duties, 50 € fee, duration, liability (left to the lawyer), personal data. Not for use before a lawyer reviews it. |
