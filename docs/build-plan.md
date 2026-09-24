# Tenderer: build plan for the whole codebase

| | |
|---|---|
| Status | In progress. M0–M3 built on 2026-09-24 (progress in §2.1); M4 onwards proposed. |
| Date | 2026-09-24 |
| Applies from | 2026-09-24: the owner started the build before the v1 gate of [`plan.md`](plan.md) §6 step 5 (3–5 real client cycles, time per cycle ≤ X). The gate still decides the v1 cut: milestones whose "Keep if" line depends on cycle evidence (M3 go/no-go, M6) wait for it. |
| Owns | Build order, milestones, deliverables, acceptance criteria, what evidence keeps or cuts each milestone, effort guesses. |
| Does not own | Architecture, paradigm and patterns per module ([`architecture.md`](architecture.md) §3–§6, summary in §6.11); strategy and gates ([`plan.md`](plan.md)); LLM choice ([`llm-models.md`](llm-models.md)); tender knowledge ([`tenders/`](../tenders/CONTEXT.md)). |

Every module named here is specified in `architecture.md`; this file says **in which order it is built and when it counts as done**. Effort figures are guesses for one developer working with AI assistance, not measurements; the first two milestones calibrate them.

---

## 0. The answer in one page

**Architecture (researched 2026-09-23 and 2026-09-24, `architecture.md` §3, §5.5, §15):** a modular monolith in Python, Django and PostgreSQL, with ports and adapters at the edges and a functional core for everything that decides deadlines, money and eligibility (AD1, AD2). It scales to every sector, procedure and country by adding **packs**, not by changing the core:

| Axis of growth | Absorbed by | A new instance costs |
|---|---|---|
| Tender | `tenders/<id>/` data: requirements, lifecycle choice, offer shape, sources | A reviewed data change |
| Sector (taxi, bus, cleaning, works, IT, supplies…) | Sector pack `sectors/<id>/`: resource kinds (JSON Schema), cost model, document types (AD13, AD15) | One package + its tests; no core change |
| Procedure type (ΔΣΑ, open, framework, negotiated, direct award) | Lifecycle templates as data in `core/lifecycle` (AD16) | One transition table |
| Offer shape (discount on reference, uniform discount, per-group discount, unit prices, lump sum, quality-price score) | Closed set of pricing strategies in `core/pricing` (AD17) | Usually none: the tender picks an existing shape |
| Country or region | Jurisdiction pack `jurisdictions/<cc>/` + `reference/<cc>/`: calendar, day counting, IDs, deductions, platform facts (AD13) | One package + reviewed calendar data |
| Data source (ΚΗΜΔΗΣ, Διαύγεια, TED…) | One adapter mapping into the OCDS-shaped opportunity model (AD14) | One adapter + contract tests |
| Operator firms | `tenant_id` from v1, PostgreSQL row-level security from v5 (AD19) | Configuration |
| Load | Not an axis until measured (§1.1 of `architecture.md`) | n/a |

**Paradigm and patterns per module:** `architecture.md` §6.11 (one table for every module, including the packs, lifecycle, opportunities and matching added on 2026-09-24).

**Build order:** a thin vertical slice first (the taxi cycle that the v0 workbook already runs), then the pieces that make a second sector cheap, then sources, extraction, portal and tenancy, each behind its own trigger (§1).

---

## 1. Phases

| Phase | Trigger (`plan.md` §6, `architecture.md` §12) | Builds | Exit gate | Effort guess |
|---|---|---|---|---|
| v1 | Step 5 gate | M0–M8 (§2): foundations, catalog, rules, pricing, lifecycle, engagements and resources, alerts, documents, audit, taxi and GR packs | `architecture.md` §12 v1 gate + §2 M8 | 12–14 weeks |
| v1.1 | Sector #2 is chosen (`plan.md` §6 step 7: categories Α and Γ of the same ΔΣΑ first) | S1 (§3): second sector pack, the scalability acceptance test | Zero changes outside the allowed paths (§3) | 2–3 weeks |
| v2 | Monitoring is sold, or client numbers make manual tracking costly | M9–M12 (§4): opportunities, ΚΗΜΔΗΣ/Διαύγεια/TED adapters, matching, job queue | `architecture.md` §12 v2 gate | 6–8 weeks |
| v3 | Onboarding a tender by hand costs more than building extraction | M13–M15 (§5): sandbox, LLM extraction, review queue | `architecture.md` §12 v3 gate | 6–8 weeks |
| v4 | Clients ask for self-service | M16 (§6): client portal | `architecture.md` §12 v4 gate | 6–10 weeks |
| v5 | A second operator firm or a second country | M17–M18 (§6): tenancy on, jurisdiction #2 | `architecture.md` §12 v5 gate | 4–6 weeks |

**What decides the v1 cut.** v1 is built only from what the concierge cycles showed (`plan.md` §6). Each milestone below names the evidence from `discovery/` time logs (blocker codes in `concierge-phase-a-2026.md` §5 and `concierge-phase-b-2026.md` §8) that keeps it in v1. Safety milestones (rules, alerts, audit) stay regardless: they protect clients from X1–X3 (`architecture.md` §1.2).

---

## 2. v1 milestones

Each milestone ends with green CI, updated `CONTEXT.md` files, and a short entry in the module's `CONTEXT.md` saying what was built. "Golden" means expected values computed independently (Decimal script or the tender's own examples), never by the code under test.

### M0. Foundations (1 week)

| | |
|---|---|
| Deliverables | `pyproject.toml` with uv lockfile (hashes); `src/tenderer/` skeleton of `architecture.md` §5.4, each created folder with `CONTEXT.md`; Django project in `shell/` (newest LTS then, §14 of `architecture.md`); PostgreSQL 17/18 in a dev container; CI: ruff (with security rules), `mypy --strict` on `core/`, pytest with branch coverage, import-linter contracts of `architecture.md` §5.3, `pip-audit`, secret scanning, `manage.py check --deploy`, the CONTEXT coverage check (`CLAUDE.md` §2) as a small script |
| Acceptance | An empty module that violates an import contract fails CI; a folder without `CONTEXT.md` fails CI; `check --deploy` passes with production settings |
| Keep if | Always |

### M1. `core/catalog` and tender schema v2 (1 week)

| | |
|---|---|
| Deliverables | `tender.toml` manifest per tender (id, sector pack, jurisdiction, lifecycle template, offer shape, source ids); `requirements.csv` schema v2 columns (`architecture.md` §6.1) plus `espd_criterion` (AD18), migrated for the current tender **together with** `tenders/CONTEXT.md` (`CLAUDE.md` §4); frozen value objects; `load_tender()`; pack registries (sector, jurisdiction) populated by `shell` |
| Acceptance | The current tender loads; any invalid row makes the whole tender fail to load, with the row and column named; `Tender.version` = git commit + file hash; property test: loading is deterministic |
| Keep if | Always (every other module reads it) |

### M2. `core/rules` and the GR jurisdiction pack (2 weeks)

| | |
|---|---|
| Deliverables | Checklist evaluator (one evaluator per `validity_kind`, three-valued results); `deadline()` with day-counting strategies from the jurisdiction pack; `jurisdictions/gr/` with the Orthodox Easter calculation checked against `reference/gr/` calendar files for 2026–2029 |
| Acceptance | 100% branch coverage; property test: no input yields SATISFIED for an UNKNOWN fact (H3); golden tests: the Easter vectors of `architecture.md` §6.2, the freshness cases the v0 workbook tests (R12 3 months, R18 30 working days, declarations after the invitation, R22 validity); a year without a calendar file marks every working-day deadline `ambiguous` |
| Keep if | Always (H1, H3) |

### M3. `core/pricing` and the taxi sector pack (1.5 weeks)

| | |
|---|---|
| Deliverables | `Money`/`Percent` value objects; the offer-shape strategies needed now (`discount_on_reference`); offer validator; go/no-go breakdown with line items; `sectors/taxi_student_transport/` cost model (fuel, wear, escort, insurance, guarantees, deductions, opportunity cost; `plan.md` §5) |
| Acceptance | Every tested case of `discovery/concierge-phase-b-workbook.xlsx` (the 134 checks of `concierge-phase-b-2026.md` §8) reproduced to the cent as golden tests; floats rejected at the boundary; mutation score recorded as the baseline (`architecture.md` §13) |
| Keep if | Go/no-go was run in the cycles (workbook in use); validator: always (H2) |

### M4. `core/lifecycle` and `apps/engagements` with resources (2 weeks)

| | |
|---|---|
| Deliverables | Lifecycle templates as data for `dps` (admission + call-off) and `open`; evaluator of transitions with guards that call `core/rules` and `core/pricing`; Django models: client, resource (kind from the sector pack, JSONB attributes validated by the pack's JSON Schema, AD15), document_record, engagement, bid, acknowledgement, all with `tenant_id` (AD19); admin screens with name + last ΑΦΜ digits on every client action (H6); ΑΦΜ check digit, plate, phone, e-mail value objects in the GR pack |
| Acceptance | Table-driven tests of every transition including illegal ones; `DRAFT → CHECKED` impossible without a clean validator, a go/no-go and no NOT_SATISFIED/UNKNOWN offer-stage item (H7); a resource with attributes that fail its schema cannot be saved; the prohibited data of `architecture.md` §8 has no field anywhere (schema review test) |
| Keep if | Always (it is the record the other modules act on) |

### M5. `apps/alerts` (1.5 weeks)

| | |
|---|---|
| Deliverables | Outbox table with idempotency keys; `plan_reminders`, `send_outbox`, `heartbeat` management commands run by cron; e-mail adapter (EU provider, SPF/DKIM/DMARC `p=reject`); `.ics` attachments; escalation ladder T-7/T-3/T-1; 14-day operator dashboard |
| Acceptance | Retrying a send never duplicates or skips (idempotency test); stopping the scheduler pages the operator within one period (alert drill, recorded); every e-mail carries the "we never ask for codes" line (snapshot test) |
| Keep if | Always (H1) |

### M6. `apps/documents` (1 week)

| | |
|---|---|
| Deliverables | Client plan, checklist, deadlines and go/no-go summary as HTML e-mail; draft declarations with sensitive parts left blank and the watermark of `architecture.md` §6.6 |
| Acceptance | Snapshot tests; every item shows its tender `§` and `Tender.version`; template-injection test (values are escaped) |
| Keep if | Time logs show dossier preparation (steps Β4–Β6, Β9) as a top cost; otherwise the checklist goes out as a plain e-mail from M5 and M6 waits |

### M7. `apps/audit` and access (1 week)

| | |
|---|---|
| Deliverables | Append-only `audit_event` (INSERT-only grant + trigger); correlation ids; audit of views and exports; roles `operator`, `reviewer`, `admin`; MFA (WebAuthn, TOTP fallback); identity-aware proxy in front of the admin; data-subject export and erasure actions; `purge_expired` job |
| Acceptance | An UPDATE or DELETE on `audit_event` fails for the app role; every state transition and export writes one event; purge test on synthetic data |
| Keep if | Always (H8, GDPR) |

### M8. Go-live of v1 (1 week)

| | |
|---|---|
| Deliverables | Deployment of `architecture.md` §9 in EU regions; backups with a tested restore; ASVS L2 self-review of the chapters in use; record of processing updated; DPIA threshold assessment; migration of the v0 spreadsheet data of live clients (metadata only) with a reconciliation report |
| Acceptance | `architecture.md` §12 v1 gate; one real invitation cycle run in v1 **in parallel** with the v0 workbook, with identical numbers |
| Keep if | Always |


### 2.1 Progress

| Milestone | State on 2026-09-24 | Evidence | Left for later |
|---|---|---|---|
| M0 | Built | `uv` lockfile; Django 5.2 LTS project in `shell/` (`check --deploy` passes with production settings); CI in `.github/workflows/ci.yml` with every gate listed above; a deliberate `core` → `django` import and a `core` → `shell` import each made `lint-imports` report `1 broken`; `scripts/check_context.py` fails on a folder without `CONTEXT.md` | Dev container: `compose.yaml` written, **not run** (Docker was not running). Secret scanning: GitHub's own scanning for public repositories, not a CI step (**UNVERIFIED** that it is on for this repository) |
| M1 | Built | `tender.toml` (TOML, not YAML: standard library, no new dependency); `requirements.csv` schema v2 with `tenders/CONTEXT.md`; `load_tender()` refuses the tender with every problem named by line and column | ESPD criterion UUIDs empty until checked against ESPD-EDM (AD18). Lifecycle names registered by name only until M4 |
| M2 | Built | 100% branch coverage of `core/rules`; H3 property test; the workbook's document boundaries (R1, R9, R12, R13, R18, R22); Easter vectors; draft calendars `reference/gr/holidays-2026…2029.csv` | Calendars say `reviewed=no`: until a person reviews them, every working-day deadline is `ambiguous` and reminders go by the earliest date |
| M3 | Built | `Money` rejects floats; `discount_on_reference` price, validator (errors in the workbook's order), guarantees; taxi cost model equal to the Decimal oracle that checked the workbook, for 6 routes × 100 discounts, including the edge route whose break-even is exactly 20 | Mutation-score baseline (`architecture.md` §13) not yet recorded. `Percent` value object skipped: rates are plain `Decimal` until a second use needs more |

---

## 3. v1.1: the scalability acceptance test (S1)

The claim "a new sector needs no core change" is tested, not assumed.

| | |
|---|---|
| Scope | Sector #2 chosen by the plan (first candidates: category Α buses or Γ ΕΔΟ of the same ΔΣΑ, `plan.md` §6 step 7): new `sectors/<id>/` (resource kinds, cost model, document types), its tender data, its golden tests |
| Allowed paths | `src/tenderer/sectors/<new>/`, `tenders/<new-or-same>/`, `reference/`, tests of those, `CONTEXT.md` files |
| Acceptance | A CI job lists the files changed by the S1 pull request; any path outside the allowed list fails the job. If it fails, the missing extension point is added to the core **first**, in its own reviewed change, and the job is re-run |
| Second proof, later | The first sector outside transport (e.g. cleaning or catering services, or small works with `uniform_discount`, Law 4412/2016 Art. 90) repeats S1 and also exercises a second offer shape |

---

## 4. v2 milestones: sources and matching

| ID | Milestone | Deliverables | Acceptance |
|---|---|---|---|
| M9 | `apps/opportunities` (1.5 w) | OCDS-shaped tables: opportunity (procedure), lot, item, award, contract, party (organisation only), document reference; CPV 2008 and NUTS reference data (AD14) | Round-trip test: an OCDS release fixture maps in and out without loss for the fields we keep |
| M10 | Source adapters (2.5 w) | `kimdis_api` (existing design, §6.8), `diavgeia_api` (award and registry decisions), `ted_api` (API v3 search, eForms notices; AD14) | Contract tests on recorded, anonymised fixtures; rate limits honoured (ΚΗΜΔΗΣ 350/min; TED limits UNVERIFIED, measured on first run); idempotent upsert keyed per source id; a polling gap raises an alert |
| M11 | Job queue (1 w) | procrastinate on PostgreSQL with periodic tasks replaces cron (AD21); outbox sender and pollers move onto it | Kill-and-restart test: no lost or duplicated job; dead man's switch still fires |
| M12 | `apps/matching` (2 w) | Client interest profile (CPV prefixes, NUTS, value range, pack filters); scoring in `core/matching` (pure); Greek full-text search (PostgreSQL ≥13 `greek` configuration) + `pg_trgm` for titles (AD20); weekly digest through alerts | Precision and recall measured on a hand-labelled set of 200 notices before the digest is sold; embeddings (pgvector) only if recall stays below the owner's threshold |

The weekly Διαύγεια check that runs today as a scheduled task is the manual forerunner of M10; its reports are fixtures for the `diavgeia_api` contract tests.

---

## 5. v3 milestones: extraction

| ID | Milestone | Deliverables | Acceptance |
|---|---|---|---|
| M13 | `adapters/file_sandbox` (2 w) | Parser process with no network, time/memory/CPU/page caps; patched `pypdf`, `pdfplumber`, `openpyxl` + `defusedxml` (`architecture.md` §6.9) | Malformed-file corpus (bombs, loops, oversized) never escapes the limits |
| M14 | `adapters/llm_openrouter` + `apps/extraction` (3 w) | Pipes and filters, dual extraction, verbatim-quote check, fallback chains, cost caps (`llm-models.md`) | Gold-set evaluation: 100% recall in 3 of 3 runs per chain model (`llm-models.md` §7) |
| M15 | Review queue (1.5 w) | Maker-checker approval producing a diff to `tenders/<id>/`; ESPD criterion suggestion per requirement (AD18) | An unapproved row never reaches the catalog; the diff passes the same CI as a hand-written change |

---

## 6. v4 and v5

| ID | Milestone | Deliverables | Acceptance |
|---|---|---|---|
| M16 | Client portal (v4) | Read-only first: checklist, deadlines, go/no-go; then document-metadata entry by the client | `architecture.md` §12 v4 gate (full ASVS L2 on the public surface, external penetration test) |
| M17 | Tenancy on (v5) | PostgreSQL row-level security policies on every `tenant_id` table; tenant-aware admin; per-tenant retention settings | Cross-tenant read and write attempts fail at the database, not only in the app (test with a second tenant's role) |
| M18 | Jurisdiction #2 (v5) | `jurisdictions/<cc>/` + `reference/<cc>/` calendars; that country's platform facts; TED as the common source | S1-style allowed-paths job passes for the jurisdiction |

---

## 7. Cross-cutting rules for every milestone

- **Tests first for `core/*`.** Golden values come from outside the code (the tender, the v0 workbook, an independent Decimal script).
- **Definition of done:** CI green (all gates of M0); `CONTEXT.md` of every touched folder updated; new dependency justified in its module's `CONTEXT.md`; hazard log (`architecture.md` §11) reviewed if the change touches deadlines, money, eligibility, personal data or external input (`CLAUDE.md` §4).
- **Data contracts change with their users.** A change to `requirements.csv`, `tender.toml` or a pack schema updates `tenders/CONTEXT.md` (or the pack's `CONTEXT.md`) and every existing tender in the same change.
- **No speculative packs.** A sector or jurisdiction pack is written only when a real tender needs it.

---

## 8. Open items for this plan

| Item | Status | Closes when |
|---|---|---|
| X (hours per cycle) and the v1 cut | Unknown until the step 3–4 time logs | Step 5 gate |
| Effort figures | Guesses | Re-estimated after M0 and M1 |
| Sector #2 | Chosen by the plan, not by this file | `plan.md` §6 step 7 |
| TED API rate limits and licence of notice data; eCertis API access; OCDS 1.2 status; new ΟΠΣ ΕΣΗΔΗΣ interfaces | UNVERIFIED (`architecture.md` §14) | Checked on the primary source when M10 or M15 starts |
