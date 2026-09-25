# Tenderer: target architecture (safety and security first)

| | |
|---|---|
| Status | Accepted for v1. v1 (M0–M8) built on 2026-09-24 and 2026-09-25 ([`build-plan.md`](build-plan.md) §2.1); what only go-live can close is listed there. v1.1 onwards is proposed. |
| Date | 2026-09-23; extended 2026-09-24 for every sector, procedure type and country (AD13–AD21, §5.5, §6.12–§6.16) |
| Applies from | v1. The owner started the build on 2026-09-24, before the gate of `docs/plan.md` §6 step 5, which still decides the v1 cut. |
| Owns | Architecture style, module boundaries, the paradigm and patterns of each module, safety and security controls, stack, deployment, verification. |
| Does not own | Business strategy ([`plan.md`](plan.md)); build order and milestones ([`build-plan.md`](build-plan.md)); tender knowledge ([`tenders/`](../tenders/CONTEXT.md)). |

Numbers in square brackets point to §15 (Sources). **UNVERIFIED** marks a claim not confirmed against a primary source. Legal statements are reasoned opinions, **not legal advice**; a Greek data-protection lawyer should confirm §10.8 before v1 goes live. Tender references (`§4.3.2.1` etc.) point to the ΔΣΑ διακήρυξη ΑΔΑ ΨΡΘ97ΛΛ-ΕΕΚ [30].

---

## 0. Decisions on one page

| ID | Decision | Main reason |
|---|---|---|
| AD1 | **Modular monolith**: one deployable, one PostgreSQL database | Fewest network boundaries, secrets and moving parts for a 1–3 person team; module boundaries are still enforced in CI [1][2] |
| AD2 | **Ports and adapters** at the edges, **functional core, imperative shell** inside [3][4] | The code that decides deadlines, prices and eligibility is pure, deterministic and fully testable; external systems can be swapped or faked |
| AD3 | **Tender knowledge is versioned data** (`tenders/<id>/`), parsed and validated at load | A new tender, region or vertical is a reviewed data change, not a code change |
| AD4 | **Python + Django (LTS) + PostgreSQL**, no message broker | Django's security defaults and built-in admin replace code we would otherwise write and get wrong; strongest PDF/XLSX/LLM libraries |
| AD5 | **No client documents stored, only metadata.** No criminal-record, health or exclusion answers stored, ever | Greek law allows private bodies to process criminal-offence data only for narrow purposes, with criminal penalties [22]. Not holding the data removes the risk |
| AD6 | **No public-facing surface in v1.** Operator UI behind an identity-aware proxy plus in-app MFA; clients receive e-mail and calendar files | The smallest attack surface is one that does not exist |
| AD7 | **Three-valued rule results**: satisfied / not satisfied / unknown. Unknown is displayed as not satisfied | A missing fact can never become a false "you are ready" |
| AD8 | **Conservative deadlines**: when a rule or calendar is ambiguous, remind by the earliest candidate date | A missed deadline can delete the client from the ΔΣΑ (§3.1) or forfeit a guarantee (§4.3.1.2) |
| AD9 | **Money as `decimal.Decimal`** with rounding rules taken from the tender | The offer must match what ΕΣΗΔΗΣ computes, to the cent (§4.3.2.1) |
| AD10 | **The LLM reads only public tender documents**, as text, through OpenRouter on zero-data-retention endpoints; it returns schema-bound JSON, every value carries a verbatim quote that code checks, two models extract requirements independently, and a human approves ([`llm-models.md`](llm-models.md)) | Contains prompt injection, invented content and omissions; client data never reaches the LLM |
| AD11 | **Transactional outbox + scheduled idempotent jobs + dead man's switch**, and every deadline goes out on three channels | A silent failure of reminders is the most likely way the product harms a client |
| AD12 | **Target OWASP ASVS 5.0 Level 2** | L2 is the level for applications that hold personal data [11] |
| AD13 | **Sector packs and jurisdiction packs.** Everything specific to a sector (resource kinds, cost model, document types) lives in `sectors/<id>/`; everything specific to a country (calendar, day counting, ID validators, deductions, e-procurement platform facts) in `jurisdictions/<cc>/`. Both register in plain in-repo registries | A new sector or country is a new package, not a core change. Plugin discovery (entry points, pluggy) waits until a third party ships packs [31] |
| AD14 | **Opportunity model shaped on OCDS and eForms**: procedure → lots → items; awards; contracts; organisations. Internal normalised tables; each source maps in through an anti-corruption adapter | Country- and vendor-neutral; an official eForms-to-OCDS mapping exists; eForms notices on TED are mandatory since 25 Oct 2023 [33][34] |
| AD15 | **Sector attributes in JSONB validated by the pack's JSON Schema**; no EAV tables, no table per sector | One `resource` table serves vehicles, staff, equipment and certificates; EAV is a known anti-pattern [35] |
| AD16 | **Procedure lifecycles as data**: one transition table per procedure type (ΔΣΑ, open, framework, negotiated, direct award), one evaluator. No workflow engine | Lifecycles are weeks-to-years of status plus deadlines, which a status field, the outbox and scheduled jobs already cover [36] |
| AD17 | **Offer shapes as a closed set of pricing strategies**: discount on a reference price, uniform discount, per-group discounts, unit-price schedule, lump sum, quality-price score projection. Tender data selects one | These are the shapes of Directive 2014/24 Art. 67 and Law 4412/2016 Art. 90 and 95 [37][38]; a new tender rarely needs a new shape |
| AD18 | **Requirements carry the ESPD criterion id** where one exists | Exclusion and selection checks are written once and reused across tenders and countries [39] |
| AD19 | **`tenant_id` on every business table from v1**; PostgreSQL row-level security switched on when a second operator firm joins (v5) | Almost free now; retrofitting tenancy onto live personal data is the expensive path [40] |
| AD20 | **Matching inside PostgreSQL**: CPV prefix, NUTS region, value range and pack filters, plus Greek full-text search (PostgreSQL 13+) and `pg_trgm`. Embeddings only after a measured recall gap | No search cluster or vector database to run and secure [41] |
| AD21 | **Jobs: cron in v1, procrastinate (PostgreSQL queue with periodic tasks) from v2** | v1 has four jobs; v2 polls several sources and needs retries and locks without adding a broker [42] |

---

## 1. Drivers

### 1.1 Quality attributes, in priority order

1. **Safety of client-affecting outputs**: deadlines, offer prices, eligibility, document checklists. An error costs the client money or a contract.
2. **Security and privacy**: data about self-employed people is personal data under GDPR. A breach harms clients and would end the business.
3. **Changeability along the domain axis**: new tenders, regions and verticals arrive as data.
4. **Operability by 1–3 people**: few moving parts, managed services, low running cost.
5. **Performance and load**: low priority. Tens to hundreds of clients; at most thousands of public notices a day.

**What "scalable" means here.** The number of tenders, sectors, procedure types, countries, data sources and (later) operator firms grows; the request rate does not. Adding a tender needs no code change (AD3); adding a sector or a country adds one pack and touches no core module (AD13, §5.5). Scaling for load is a non-goal until a measurement shows a need.

### 1.2 Harms we design against (safety)

| ID | Harm to the client | Example from the current tender |
|---|---|---|
| X1 | Deleted from the ΔΣΑ | Renewed ΕΕΕΣ not sent within 5 working days (§3.1) |
| X2 | Offer rejected | Paper participation guarantee not delivered before opening (§4.3.1.2); price above budget (§4.3.2.3) |
| X3 | Guarantee forfeited, award lost | Provisional-award documents not submitted within 10 days (§5.3.1, §4.3.1.2) |
| X4 | Loss-making contract | Discount fixed for 3 years with no fuel adjustment for taxis (§6.6.4); route cancelled without compensation (§7.6.1) |
| X5 | Wrong price entered | A decimal discount is rounded **up** by ΕΣΗΔΗΣ (§4.3.2.1) |
| X6 | Personal data exposed | Leak of names, tax IDs, phone numbers, plates |
| X7 | Acting on a fake message | Phishing that imitates our reminders or asks for ΕΣΗΔΗΣ/Taxisnet credentials |

### 1.3 Constraints

- Product invariants, [`CLAUDE.md`](../CLAUDE.md) §5: no client credentials; never sign or submit for the client; no sensitive documents; the client decides the discount.
- The plan's gates, `plan.md` §6: the owner started the build before step 5 (2026-09-24); build only what real client cycles showed is needed.
- Client personal data and its processing stay in the EU. The one exception, public tender text sent to the LLM, is covered in §10.8.

---

## 2. Principles

**Safety**

| ID | Principle | In practice |
|---|---|---|
| S1 | Fail safe | Unknown, stale or unparseable input produces "not ready" plus a visible reason, never a green tick |
| S2 | State the uncertainty | Every result carries its status and the reason for it |
| S3 | A human decides at irreversible steps | The client signs and submits; an operator approves extracted data; the software never submits, signs or picks a discount |
| S4 | Traceability | Every checklist, deadline and price stores its inputs, the tender-data version (git commit + file hash) and the tender `§` it relies on |
| S5 | Redundancy for time-critical signals | More than one channel per deadline, plus a monitor that notices when the reminder machinery itself stops |
| S6 | Conservative arithmetic | Earliest candidate deadline; exact decimal money; rounding exactly as the tender specifies |
| S7 | Simplicity | Every component is a failure mode; each one must earn its place |

**Security**

| ID | Principle | In practice |
|---|---|---|
| C1 | Minimise data | Collect only what the service needs; the safest record is one never stored (GDPR Art. 5(1)(c), Art. 25) |
| C2 | Minimise surface | No public endpoint until a feature needs one |
| C3 | Least privilege | People, database roles, API keys, CI tokens |
| C4 | Defence in depth | No single control is trusted alone |
| C5 | External input is hostile | Tender files, API responses, e-mail and LLM output are parsed defensively and isolated |
| C6 | Use secure defaults, do not rebuild them | CSRF, escaping, sessions, CSP, admin come from the framework |
| C7 | Know the supply chain | Few dependencies, pinned by hash, audited in CI |

---

## 3. Architecture style: options and choice

| Option | Safety | Security | Domain changeability | Operability (1–3 people) | Verdict |
|---|---|---|---|---|---|
| Spreadsheet / no-code (Sheets, Airtable + automations) | Formulas hard to test; no audit trail | Personal data in third-party SaaS; sharing links leak | Poor | Excellent | **v0 only** (§12) |
| Microservices | Distributed state makes deadline logic harder to get right | Every service adds endpoints, secrets and service-to-service auth | Good | Poor | Rejected [1] |
| Serverless functions | Scheduling and retries spread across cloud configuration | Many IAM policies to get right; harder to test locally | Fair | Fair | Rejected for v1 |
| Event sourcing / CQRS | Replay helps audits | Erasure of personal data from an immutable event store is hard | Fair | Poor | Rejected: an append-only audit log gives the traceability we need |
| **Modular monolith + ports and adapters + functional core** | Pure core, exhaustively testable | One deployable, one database, one set of secrets | Good (tenders as data) | Excellent | **Chosen** |

**Why the chosen option is the best fit here**

- **Correctness where it matters.** Deadline, price and eligibility logic sits in pure functions with no I/O and no hidden clock. Pure functions can be tested exhaustively (property-based and golden tests, §13), and any past result can be recomputed from its recorded inputs (S4) [4].
- **Smallest attack surface.** One process, one database, no broker, no internal network calls. The only inbound path is the operator UI behind an identity-aware proxy.
- **Boundaries without distribution.** Modules are Python packages whose import rules are checked in CI (§5.3). If a measured need ever appears, a module can be extracted into a service; that is the path recommended for small teams: build a monolith first and split only when a specific pain justifies it [1][2].
- **Domain scaling by data.** Tender specifics live in `tenders/<id>/`. Tender #2 is a reviewed data change, plus at most one new pricing strategy (§6.3).
- **Rules as data, not a rules engine.** General rules engines hide program flow and the promise that non-developers will maintain the rules "rarely works out in practice" [6]. Decision tables in CSV with small typed evaluators give the benefit without the engine.

---

## 4. Stack

| Layer | Choice | Why | Rejected alternatives |
|---|---|---|---|
| Language | **Python 3.13** or newer, within the range the chosen Django version supports (Django 6.1: 3.12–3.14 [18]) | Best libraries for PDF/XLSX parsing; `decimal` and `zoneinfo` in the standard library; Hypothesis [10] | TypeScript (weaker PDF/table extraction); Go (more code for CRUD and admin) |
| Web framework | **Django, the newest LTS available when v1 starts.** Today: 5.2 LTS, security fixes until 30 Apr 2028. 6.0 (3 Dec 2025) added built-in CSP; 6.1 released 5 Aug 2026 [18][19]. The next LTS, 6.2, is expected around April 2027 (**UNVERIFIED**). On 5.2, add CSP with the `django-csp` package | The admin is the operator UI for free; CSRF protection, template auto-escaping, clickjacking protection and secure sessions by default; migrations; parameterised ORM queries | FastAPI, Flask (security features assembled by hand; no admin) |
| Database | **PostgreSQL 17 or 18**, managed, EU region. Not 14 (end of life 12 Nov 2026); Django 6.1 needs 15+ [21][18] | CHECK and UNIQUE constraints enforce invariants in the database; roles and grants give an append-only audit table; point-in-time recovery | SQLite (no role separation; fine only for throwaway prototypes) |
| Background work | **Cron (or the platform scheduler) calling Django management commands**, with a transactional outbox table [7] | No broker to run or secure; a handful of idempotent jobs | Celery + Redis (extra service and attack surface). Django 6.0's `django.tasks` ships only non-production backends and needs a third-party worker [8]; from v2, **procrastinate** (PostgreSQL only, periodic tasks, retries, locks; 3.10.0 on 2026-09-23) replaces cron when several sources are polled (AD21) [42] |
| LLM (v3) | **OpenRouter** in front of several model vendors, called with `httpx` over its REST API. Models, fallback order and request settings: [`llm-models.md`](llm-models.md) | One integration reaches Anthropic, OpenAI and Google models, so one vendor's outage or failed evaluation does not stop extraction; zero-data-retention and EU-first routing per request; model prices equal the vendors' own [29] | Each vendor's own SDK (one integration, key and contract per vendor); the `openai` SDK pointed at OpenRouter (an extra dependency for one POST endpoint) |
| Dependencies | **uv** with a hash-pinned lockfile; `pip-audit` in CI [17] | Reproducible builds; blocks silent package substitution | Unpinned `requirements.txt` |
| Boundary checks | **import-linter** 2.x (`layers`, `independence`, `forbidden` contracts) [5] | One config file, one CLI call in CI; the longest track record | tach, pytestarch (both viable, less established for this use) |

---

## 5. Module map

### 5.1 Overview

```
  operator ──► identity-aware proxy (MFA) ──► Django admin
                                                   │
┌──────────────────────────── shell (Django project) ─────────────────────────────┐
│ admin UI · management commands (scheduled jobs) · settings · wiring             │
├─────────────────────────────── application modules ─────────────────────────────┤
│ engagements · alerts · documents · audit                                        │
│ opportunities · ingestion · matching (v2) · extraction (v3)                     │
├─────────────────────────────────── core (pure) ─────────────────────────────────┤
│ catalog · rules (checklists, deadlines) · pricing · lifecycle · matching        │
├──────────────────────────────── packs (pure, data) ─────────────────────────────┤
│ sectors/<id> (taxi_student_transport, …) · jurisdictions/<cc> (gr, …)           │
├───────────────────────────────────── adapters ──────────────────────────────────┤
│ kimdis_api · diavgeia_api · ted_api · llm_openrouter · mailer · file_sandbox    │
└─────────────────────────────────────────────────────────────────────────────────┘
        ▲ public data only                              ▲ public data only
   ΚΗΜΔΗΣ, Διαύγεια, TED APIs                       OpenRouter
```

### 5.2 Dependency rules

1. `core/*` imports only the standard library and other `core/*` packages: no Django, no HTTP, no database, no clock. The current date is a parameter.
2. Application modules import `core/*` and port interfaces, never concrete adapters.
3. Adapters implement ports and may import third-party client libraries.
4. Only `shell` wires adapters into modules.
5. **`ingestion` and `extraction` must not import `engagements`.** They can never see client data, so "no client data reaches the LLM" (AD10) is enforced by the build, not by discipline.
6. Application modules call each other only through the functions in each module's `api.py`, never through another module's models.
7. **Packs** (`sectors/*`, `jurisdictions/*`) import only the standard library and `core/*` types; they never import Django, adapters or each other. `core/*` never imports a pack: it defines the protocols (`SectorPack`, `JurisdictionPack`) and receives packs through the registries that `shell` fills at start-up. Application modules reach a pack only through those registries, never by name.

### 5.3 Enforcement in CI

- import-linter contracts [5]: one `layers` contract (shell → apps → core); `forbidden` contracts (`core` and packs must not import `django`, `requests`, `httpx`; packs must not import apps or adapters; `core` and apps must not import packs, since only `shell` does; `ingestion` and `extraction` must not import `engagements`); `independence` contracts between application modules except through `api.py`, between sector packs, and between jurisdiction packs.
- The scalability acceptance test of [`build-plan.md`](build-plan.md) §3: a pull request that adds a sector or jurisdiction may change only that pack, tender data, `reference/` and their tests.
- A CI check fails when a folder has no `CONTEXT.md` or a file is missing from its folder's `CONTEXT.md` (`CLAUDE.md` §2).

### 5.4 Folder layout (each folder is created only when its module is built)

```
src/tenderer/
  core/catalog/   core/rules/   core/pricing/   core/lifecycle/   core/matching/ (v2)
  sectors/taxi_student_transport/   sectors/<id>/ …      (one package per sector, AD13)
  jurisdictions/gr/                 jurisdictions/<cc>/ … (one package per country, AD13)
  apps/engagements/   apps/alerts/   apps/documents/   apps/audit/
  apps/opportunities/ apps/ingestion/ apps/matching/       (v2)
  apps/extraction/                                         (v3)
  adapters/kimdis_api/  adapters/diavgeia_api/  adapters/ted_api/
  adapters/llm_openrouter/  adapters/mailer/  adapters/file_sandbox/
  shell/                (settings, urls, admin site, management commands, pack registration)
tests/                  (one test file per module)
tenders/                (exists: tender modules as data; each gets a `tender.toml` manifest when `core/catalog` is built)
reference/              (exists: dated snapshots of external data, e.g. the OpenRouter model catalog)
reference/gr/           (Greek public-holiday calendar per year, reviewed data)
reference/cpv/, reference/nuts/   (classification lists, v2)
```

Each folder receives its own `CONTEXT.md` when it is created.

### 5.5 Scaling across sectors, procedures and countries

The core knows about tenders, requirements, resources, deadlines, offers and money; it knows nothing about taxis, Greece or ΕΣΗΔΗΣ. Everything specific enters through one of five extension points, each with a fixed contract:

| Extension point | Contract (typed, in `core/*`) | Supplied by | Example |
|---|---|---|---|
| Tender | `tender.toml` + `requirements.csv` (§6.1) | `tenders/<id>/` data | the ΔΣΑ of this repo |
| Sector | `SectorPack`: resource kinds with JSON Schemas, a cost-model strategy for go/no-go, document types, default warnings | `sectors/<id>/` (§6.12) | vehicle, driver and escort kinds; fuel and wear costs; the fuel-risk warning of §6.6.4 |
| Procedure type | Lifecycle template: states, transitions, guards named by id (§6.14) | data in `core/lifecycle` | `dps`: admission, call-off, award, contract |
| Offer shape | Pricing strategy keyed by `offer_shape` (§6.3) | `core/pricing` (closed set) | `discount_on_reference`, `uniform_discount` |
| Country | `JurisdictionPack`: calendar and day-counting strategies, ID validators, deductions on payments, platform facts | `jurisdictions/<cc>/` + `reference/<cc>/` (§6.13) | ΑΦΜ check digit, Orthodox Easter, Regulation 1182/71 conventions, the 0.12432% deductions |
| Data source | Port `ProcurementSource` → OCDS-shaped opportunity (§6.15) | `adapters/*` | ΚΗΜΔΗΣ, Διαύγεια, TED |

Why packs and not the alternatives:

| Option | Verdict |
|---|---|
| A Django app per sector with its own models | Rejected: N sets of migrations and admin screens, and cross-sector queries need unions |
| EAV tables for sector attributes | Rejected: no types, one join per filtered attribute [35] |
| Plugin discovery (entry points, pluggy) | Deferred: pays off only when packs are installed independently by third parties [31] |
| A rules or workflow engine | Rejected: §3 and [6], [36] |
| **Pure in-repo packs registered by `shell`, attributes in JSONB validated by JSON Schema** | **Chosen**: one set of tables, typed contracts, packs testable without a database |

The proof is a test, not a promise: [`build-plan.md`](build-plan.md) §3 fails the build of sector #2 if it touches anything outside its pack and its data.

---

## 6. Modules: responsibility, paradigm, patterns, controls

### 6.1 `core/catalog`: tender knowledge as data

| | |
|---|---|
| Responsibility | Load `tenders/<id>/` into typed, immutable objects; refuse invalid data |
| Paradigm | Declarative data + functional parsing ("parse, don't validate" [9]) |
| Patterns | Value Object (frozen dataclasses) [9]; Registry (tender id → module); schema-version check; content hash for traceability |
| Interface | `load_tender(path) -> Tender`; `Tender.requirements: tuple[Requirement, ...]`; `Tender.version` (git commit + file hash) |
| Safety | A tender with any invalid row does not load at all (fail closed, S1). Every result made from a tender stores `Tender.version` (S4). Data changes arrive as reviewed pull requests |
| Security | Reads repository files only; no network; no personal data |
| Build | v1 |

**Schema v2 for `requirements.csv`** (needed by `core/rules`; add it when `rules` is built, following `CLAUDE.md` §4). Machine-readable columns go next to the existing human text:

| Column | Values | Example (R12) |
|---|---|---|
| `doc_type` | Stable key that joins to document metadata | `criminal_record_extract` |
| `applies_to` | `client`, `offer`, `engagement`, or a resource kind of the sector pack (`vehicle`, `driver`, `escort` for taxis) | `client` |
| `validity_kind` | `in_force`, `issued_within`, `signed_after`, `valid_until`, `none`, `manual` | `issued_within` |
| `validity_amount`, `validity_unit` | Integer; `days`, `working_days`, `months` | `3`, `months` |
| `validity_anchor` | `submission`, `invitation_sent`, `offer_validity_end`, `contract_end` | `submission` |

| `espd_criterion` | ESPD criterion id (ESPD-EDM static UUID) when the requirement is an exclusion or selection criterion; empty otherwise (AD18) [39] | empty for R12 (national evidence document); the id of the "criminal convictions" ground for the ΕΕΕΣ answer it proves |

`manual` is for rules the tender leaves vague, e.g. R16 "recent". The evaluator returns *unknown* for them and an operator checks by hand (S1).

**`tender.toml` manifest** (one per tender folder, added with `core/catalog`; TOML because Python reads it with the standard library, and rates are decimal strings because TOML floats are binary): `id`, `sector` (pack id), `jurisdiction` (pack id), `lifecycle` (template id, §6.14), `offer_shape` (§6.3), `rounding`, `sources` (ΑΔΑ, ΚΗΜΔΗΣ reference, OCDS id when one exists), `schema_version`. The catalog refuses a tender whose pack, template or shape is not registered (fail closed, S1).

### 6.2 `core/rules`: checklists and deadlines

| | |
|---|---|
| Responsibility | (a) For one engagement and one planned submission, the status of every requirement. (b) Every deadline, from its legal rule and the holiday calendar |
| Paradigm | Pure functional: total functions, immutable inputs, no I/O, no clock reads; decision tables for validity rules |
| Patterns | Decision table / Specification (one small evaluator per `validity_kind`, kept in a dict, not a class hierarchy); Result objects for business outcomes instead of exceptions; Strategy for day-counting conventions, supplied by the jurisdiction pack (§6.13) so that another country's rules plug in without touching the evaluator |
| Security | No personal data leaves the function; inputs are value objects |
| Build | v1 |

Interface sketch:

```
evaluate(requirements, documents, key_dates, today) -> Checklist
    item = (requirement_id, status ∈ {SATISFIED, NOT_SATISFIED, UNKNOWN}, reason, source_section)
deadline(event_at, rule, calendar) -> Deadline(remind_by, legal_latest, ambiguous: bool, note)
```

Safety rules:

- **Three-valued logic.** `UNKNOWN` renders exactly like `NOT_SATISFIED`, with its reason (AD7).
- **Freshness is checked against the planned submission date, not today.** A document valid today can be stale on submission day (e.g. R12: issued ≤3 months before submission, §5.3.2).
- **Time.** `Europe/Athens` through `zoneinfo`; stored in UTC; the cut-off time comes from the invitation (e.g. 23:59:59, or 13:00 in the August 2026 negotiated procedure).
- **Day counting.** Procurement periods follow Regulation 1182/71 [27]: by secondary sources, the day of the event is not counted and a period ending on a Saturday, Sunday or public holiday runs to the end of the next working day (**UNVERIFIED** against the primary text). The engine computes every plausible convention and sets `remind_by` to the earliest result; `legal_latest` is shown only as information (AD8, S6).
- **Working days come from a reviewed calendar file per year** (`reference/gr/`), not only from a formula. The moveable holidays follow Orthodox Easter, and a fixed holiday can be moved by government decision (**UNVERIFIED** example: Labour Day 2024). Whit Monday (Αγίου Πνεύματος) is a non-working day for the public sector, so it counts as non-working for deadlines that run against contracting authorities [27]. A year without a reviewed calendar makes every working-day deadline in that year `ambiguous` (S1).
- **Test vectors.** Computed with the Meeus Julian algorithm and matching the published 2026 list [27]. Orthodox Easter: 2026-04-12, 2027-05-02, 2028-04-16. Clean Monday: 2026-02-23, 2027-03-15, 2028-02-28. Good Friday: 2026-04-10, 2027-04-30, 2028-04-14. Whit Monday: 2026-06-01, 2027-06-21, 2028-06-05. In 2027, Labour Day (1 May) falls on Holy Saturday, so the calendar file must record whatever the government decides that year.

### 6.3 `core/pricing`: reference prices, offer validation, go/no-go

| | |
|---|---|
| Responsibility | Reference price per route (tender-specific formula); validation of the offer the client intends to type into ΕΣΗΔΗΣ; go/no-go breakdown (`plan.md` §5) |
| Paradigm | Pure functional with value objects |
| Patterns | Value Objects `Money` (Decimal plus ISO 4217 currency; EUR today) and `Percent`; Strategy registry keyed by the formula id declared in the tender data (e.g. the taxi formula of ΚΥΑ 50025/2018, based on Tariff 2, §6.6.4); a second Strategy registry keyed by `offer_shape` (below); the cost model of go/no-go comes from the sector pack (§6.12); explainable computation (every result carries its line items) |

**Offer shapes (AD17).** A closed set; the tender's `tender.toml` picks one. Each shape has its own validator and its own go/no-go input:

| `offer_shape` | What the client offers | Where it occurs | Build |
|---|---|---|---|
| `discount_on_reference` | Integer discount per route or group on a published reference price | This ΔΣΑ (§4.3.2) | v1 |
| `uniform_discount` | One discount on the whole priced bill | Public works, Law 4412/2016 Art. 90 [38] | with the first works tender |
| `group_discounts` | One discount per group of works items | Public works, Law 4412/2016 Art. 95 [38] | with the first tender that needs it |
| `unit_prices` | A price per line of a bill of quantities; total = Σ quantity × unit price | Supplies and services | with the first tender that needs it |
| `lump_sum` | One total price | Supplies and services, lowest price or lowest cost (Directive 2014/24 Art. 67) [37] | with the first tender that needs it |
| `quality_price_score` | Price plus quality sub-criteria; the tool projects the score from the tender's formula and weights, it never scores the quality part itself | Best price-quality ratio (Art. 67) [37] | with the first tender that needs it |

The discount itself is never proposed, whatever the shape (`CLAUDE.md` §5).
| Security | No personal data; pure |
| Build | v1 (replaces the spreadsheet of `plan.md` §5) |

Interface sketch:

```
validate_offer(offer, route_group, pricing_rules) -> list[Violation]
go_no_go(route, cost_inputs, discount) -> Breakdown(net_per_day, net_per_year, break_even_discount, lines)
```

Safety rules:

- `decimal.Decimal` only; floats are rejected at the boundary; the rounding policy is tender data. For the current tender: prices to 2 decimals, half up; integer discount; a decimal discount is rounded up by ΕΣΗΔΗΣ, so the validator blocks it (§4.3.2.1) (AD9).
- Validator rules for the current tender (§4.3.2): integer discount; EUR; VAT excluded; price ≤ budget; one discount per route group; the offer template (Annex III of the tender, Annex II in both 2026 taxi invitations) matches the ΕΣΗΔΗΣ form and states the discount in words; a vehicle may serve several routes only in different operating zones, declared in the remarks field. The v0 spreadsheet (`discovery/concierge-phase-b-workbook.xlsx`) implements these rules and the go/no-go; its tested cases are golden-test candidates for v1.
- It never proposes a discount. It shows the break-even discount and the full computation (`CLAUDE.md` §5).
- Every taxi go/no-go shows the fuel risk (no fuel adjustment, §6.6.4) and the cancellation risk (§7.6.1) as explicit warnings.

### 6.4 `apps/engagements`: clients, vehicles, document metadata, lifecycle

| | |
|---|---|
| Responsibility | The records the service needs about a client and the client's resources (vehicles, staff, equipment, certificates: any kind a sector pack defines), and the lifecycle of each client × tender engagement and each bid |
| Paradigm | Object-oriented domain model persisted with the Django ORM (active record). Decisions are delegated to `core/*`; models hold identity, state and invariants |
| Patterns | Entity; Value Objects validated at the boundary (ID validators from the jurisdiction pack, e.g. ΑΦΜ with check digit; plate; E.164 phone; e-mail); **State machine** driven by the lifecycle template of the tender's procedure type (§6.14); **typed JSONB**: one `resource` table whose `attributes` are validated against the sector pack's JSON Schema on every write (AD15); Repository = the Django model manager (no extra repository layer); services for writes and selectors for reads, per module [43] |
| Build | v1 |

State machines of the `dps` lifecycle template, the one this ΔΣΑ uses (§6.14; other procedure types have their own tables; each transition writes an audit event; an illegal transition raises):

```
Engagement: ONBOARDING → REGISTERED (ΕΣΗΔΗΣ) → APPLIED (ΕΕΕΣ) → ADMITTED → CONTRACTED → CLOSED
            any → WITHDRAWN;  APPLIED → REJECTED
Bid (one per invitation): DRAFT → CHECKED → CLIENT_SUBMITTED → AWARDED | NOT_AWARDED
            guard DRAFT → CHECKED: offer validator clean AND go/no-go recorded
                                   AND no NOT_SATISFIED/UNKNOWN item for the offer stage
```

Safety: every screen that acts on a client shows the client's name and the last digits of the ΑΦΜ (prevents wrong-client errors).

Privacy by design (AD5):

| Stored | Never stored |
|---|---|
| Name, ΑΦΜ, phone, e-mail | Document files of any kind |
| Vehicles: plate, category, seats, base municipality | Content of criminal-record extracts; health data |
| Drivers: display name, licence expiry dates | Answers to exclusion questions (§2.2.3). Only "client confirmed on date X that they reviewed the exclusion grounds" |
| Document metadata: type, issue date, expiry, who saw it, when | Whether a criminal-record extract is clean. For R12 only the issue date is recorded; the client judges the content |
| Engagement and bid state, offer numbers | Credentials, signatures, signing keys |

- Retention: personal data is purged N months after the engagement closes (N set in the retention schedule, §10.8); the `purge_expired` job enforces it.
- Data-subject requests: export and erasure as admin actions, both audited (`apps/privacy`, M7). Erasure is refused while an engagement is still open. `purge_expired` needs N and refuses to run without it.

### 6.5 `apps/alerts`: reminders that must not fail silently

| | |
|---|---|
| Responsibility | Turn deadlines from `core/rules` into reminders to clients and escalations to operators |
| Paradigm | Event-driven through a transactional outbox, run by idempotent scheduled jobs |
| Patterns | **Transactional Outbox**: a state change and the notifications it causes commit in one transaction; a sender job delivers and marks them sent [7]. **Idempotency key** per notification (unique constraint), so retries cannot duplicate or skip. **Escalation ladder**: reminders at T-7, T-3, T-1 days; if the client has not acknowledged by T-3 the operator dashboard turns red and the operator phones. **Dead man's switch**: each job run pings an external monitor, and a missing ping pages the operator |
| Build | v1 |

- Safety (S5): three independent channels per deadline: e-mail; a calendar file (`.ics`) sent when the deadline is created, so it lives in the client's own calendar even if our system is down; the operator dashboard of the next 14 days.
- Security: reminders carry the minimum (tender, step, date); they never contain a link that asks for credentials; every e-mail states that we never ask for ΕΣΗΔΗΣ or Taxisnet codes (X7). The sending domain has SPF, DKIM and DMARC `p=reject`. Calendar data is an attachment, never a public feed URL.

### 6.6 `apps/documents`: what the client receives

| | |
|---|---|
| Responsibility | Personalised checklist, deadlines, draft declarations (text to paste into gov.gr), go/no-go summary |
| Paradigm | Declarative templates; rendering is a pure function of the data |
| Patterns | Template (Django templates with auto-escaping); snapshot (golden) tests; every draft is watermarked "ΠΡΟΣΧΕΔΙΟ – ελέγξτε πριν υπογράψετε" |
| Safety | Each item shows its tender `§` and the tender-data version (S4) |
| Security | Templates are code, never user input (prevents template injection); every value is escaped. Declarations are generated blank for the sensitive parts: the client fills and signs them in gov.gr, so the content never passes through our systems |
| Build | v1 as HTML e-mail + `.ics` (M6, `apps/documents`); PDF only when a client asks for it. Draft declaration texts are tender data: `tenders/<id>/declarations/<requirement>.txt`, reviewed like `requirements.csv` |

### 6.7 `apps/audit`: append-only record

| | |
|---|---|
| Responsibility | Who did what and when: sign-ins, views and exports of client data, state transitions, overrides, deliveries, the tender-data version behind each result |
| Paradigm | Append-only event log |
| Patterns | Append-only table enforced by the database: the app role has `INSERT` and `SELECT` only, and a `BEFORE UPDATE OR DELETE` trigger raises as a second layer [21]; correlation id per request and job |
| Security | Event details hold internal ids, not personal data; retention per schedule |
| Build | v1, built in M7: `apps/audit` (trigger in migration 0002, grants in `deploy/roles.sql`, both tested); every other module writes through `audit.api.record`; admin screens with client data derive from `AuditedAdmin` |

### 6.8 `apps/ingestion` + `adapters/kimdis_api`: public procurement data

| | |
|---|---|
| Responsibility | Poll the ΚΗΜΔΗΣ OpenData API for notices and contracts by CPV (60130000-8 today; any CPV list a client profile needs from v2) and organisation; map them into `opportunities` (§6.15); download attachments. Διαύγεια and TED follow the same design as further adapters behind the same port |
| Paradigm | Imperative shell around pure mapping functions |
| Patterns | Gateway/Adapter behind a port (`ProcurementRegistry`); Anti-Corruption Layer (external JSON → validated internal types); retry with exponential backoff and jitter that honours `Retry-After`; client-side token bucket below the published 350 requests/minute [28]; stop-and-alert after repeated failures (a minimal circuit breaker); idempotent upsert keyed on `referenceNumber`; checkpoint of the last complete time window |
| Safety | A gap in polling is itself an alert (S5); every notice shows its `referenceNumber` and source link so the operator checks the original |
| Security | Host allowlist; TLS verification on; timeouts; response-size caps; JSON checked against the expected shape; attachments stored with SHA-256 and size, parsed only in the sandbox (§6.9). The data is CC BY 4.0, so attribution is kept [28]. **Only the documented OpenData API is automated**; the ΕΣΗΔΗΣ submission portal is never scripted (its terms on automated access are **UNVERIFIED**, and scripting it would also break the no-credentials invariant) |
| Build | v2, when monitoring becomes a paid feature. Before that, the desk research of `plan.md` §6 step 1 is a one-off script |

### 6.9 `apps/extraction` + `adapters/file_sandbox` + `adapters/llm_openrouter`: from public files to reviewed data

| | |
|---|---|
| Responsibility | Turn a tender's files into *candidate* rows (requirements, route tables) for human review. It never writes to the catalog: its output is a proposed diff to `tenders/<id>/` |
| Paradigm | Pipes and filters (each stage a pure function from one representation to the next), with I/O only at the ends, plus a human approval step |
| Patterns | Chain of Responsibility (parser fallbacks, then the LLM fallback chain run by our code); Strategy per file format; N-version extraction (two independent models, union reviewed); Sandbox; Maker-Checker; staging area |
| Build | v3, when onboarding tender #2 by hand costs more than building this |

Pipeline:

1. File in (from `ingestion` or an operator upload) → type and size check → SHA-256.
2. Deterministic parsers first, inside the sandbox: XLSX with `openpyxl` (with `defusedxml` installed), then PDF tables with `pdfplumber`.
3. The LLM only for what step 2 cannot handle, e.g. free-text requirements.
4. **Verification.** Every extracted value carries `page` and a verbatim `quote`; code checks that the quote occurs in that page's text, as extracted by the sandboxed parser. A mismatch is rejected, never silently fixed.
5. **Review queue.** An operator approves each row (maker-checker); approval produces the diff, and CI validates it like any other change to `tenders/`.

LLM design (OpenRouter [29]; models, fallback order and every request setting are in [`llm-models.md`](llm-models.md)):

- Input: public tender documents only (dependency rule 5), sent as the page-marked text the sandboxed parser produced, never as files. Every model then sees exactly the text the quote check uses, and no PDF plugin or OCR service becomes one more processor. Tender documents still contain names of civil servants, which are personal data; §10.8 covers the transfer.
- Routing: every request is pinned to zero-data-retention endpoints that support every parameter sent, EU region first, and the OpenRouter account allows only the chain's models and providers.
- Output: a JSON Schema in `response_format` with `strict: true`, validated again by our own schema, because some providers treat a schema as a hint rather than a guarantee.
- Models: requirements are extracted by two models from different vendors on every tender, and the reviewer sees the union, because the quote check catches invented values but not omissions. A third model replaces either one if it fails. No model enters a chain before it passes the gold-set evaluation; the hand-built `requirements.csv` of the current tender is the first gold tender.
- Fallback is our code's job, not OpenRouter's: its `models` array falls back only on errors, while an answer that ends with `length`, is empty or fails our schema must also move to the next model.
- Reasoning is on, with effort set per task, and the reasoning text is excluded from the response: it is never stored or shown. Reasoning tokens are billed as output and count against `max_tokens`.
- Every finish reason other than `stop` is a failed run, including `length` and empty content (billed, still failed); a partial answer is never used.
- No `temperature`, `top_p`, `top_k` or `seed` is sent: Claude and GPT-6 do not accept them while reasoning, and Google recommends Gemini's default, so every call runs at temperature 1. No temperature makes answers repeatable, so the stored answer is the record (S4).
- Budget: `max_tokens` and `max_price` per request, a per-key credit limit and a daily spend limit on the OpenRouter account, usage and cost logged per attempt.
- Batch requests and prompt caching are not used; at our volume they would save a few dollars a month.

OWASP Top 10 for LLM Applications 2025 [13]:

| Risk | Control |
|---|---|
| LLM01 Prompt injection (instructions hidden in a tender PDF) | Document content is marked as data in the prompt; the model has no tools; output is schema-bound; quotes are verified; a human approves |
| LLM02 Sensitive information disclosure | No client data is ever sent (dependency rule 5); zero-data-retention endpoints only |
| LLM03 Supply chain | Model and provider allowlists on the OpenRouter account; a model enters a chain only after the gold-set evaluation; a new endpoint snapshot triggers re-evaluation |
| LLM05 Improper output handling | Output is untrusted: schema-validated, rendered with escaping in the admin (prevents XSS), never executed |
| LLM06 Excessive agency | No tools and no permissions; code decides what happens next |
| LLM09 Misinformation | Verbatim-quote check, dual extraction, gold-set evaluation, human approval |
| LLM10 Unbounded consumption | `max_tokens` and `max_price` per request, file-size and page caps, per-key credit limit, daily spend limit |

Untrusted files [14][15][16]:

- Parsing runs in a separate process (container) with **no network**, a wall-clock timeout, memory and CPU limits, and file-size and page caps.
- Parser versions are pinned at or above the fixed releases: pypdf ≥ 6.4.0 (CVE-2025-62707 infinite loop, CVE-2025-66019 memory exhaustion); pdfminer.six (and therefore pdfplumber) at a release that fixes both CVE-2025-64512 (code execution through `pickle`) and CVE-2025-70559 (its incomplete first fix); confirm the fixed version in the advisory before v3. The sandbox is required because of bugs like these, not optional.
- `defusedxml` is installed so that `openpyxl` parses XML with the hardened parser (protection against XML bombs).

### 6.10 `shell`: Django project, admin, jobs

| | |
|---|---|
| Responsibility | Settings, wiring, operator UI (Django admin), management commands run by the scheduler: `send_outbox`, `heartbeat` (both in `apps/alerts`, M5), `purge_expired`, `plan_reminders` (only once deadlines arrive outside a transaction, v2) and `poll_sources` (v2) |
| Paradigm | Framework-driven; kept thin |
| Patterns | 12-factor configuration (environment variables); dependency injection by passing adapters as function arguments (no DI container) |
| Security | Access in §10.2; `manage.py check --deploy` passes in CI [19] |
| Build | v1 |

### 6.11 Summary: paradigm and patterns per module

| Module | Paradigm | Key patterns | Why this fits |
|---|---|---|---|
| core/catalog | Declarative data + functional parsing | Value Object, Registry, parse-don't-validate | Rules change per tender, not per release; reviewed as diffs |
| core/rules | Pure functional, decision tables | Specification / decision table, Strategy, Result | Deadlines and eligibility must be exhaustively testable and replayable |
| core/pricing | Pure functional + value objects | Money/Percent value objects, Strategy registry, explainable computation | Cent-exact money; formulas differ by vertical |
| apps/engagements | OO domain model on the ORM | Entity, Value Object, State machine | Identity and lifecycle; illegal transitions are impossible |
| apps/alerts | Event-driven + scheduled jobs | Transactional Outbox, idempotency key, escalation, dead man's switch | No lost or duplicated reminders; silent failure is detected |
| apps/documents | Declarative templates | Template, snapshot tests | Presentation separate from logic; escaping by default |
| apps/audit | Append-only event log | Database-enforced append-only, correlation id | Tamper resistance, traceability |
| apps/ingestion | Imperative shell + pure mapping | Gateway, Anti-Corruption Layer, retry/backoff, rate limiter, idempotent upsert | I/O with an external system that fails and rate-limits |
| apps/extraction | Pipes and filters + human workflow | Chain of Responsibility, Strategy, N-version extraction, Sandbox, Maker-Checker | Untrusted input; every stage testable; omissions caught by a second model; a human approves |
| shell | Framework-driven | 12-factor configuration, DI by argument, pack registration | Django's secure defaults; thin wiring |
| sectors/* (§6.12) | Declarative data + pure functions | Plugin by registry, Strategy (cost model), JSON Schema per resource kind | A new sector is a package, not a core change |
| jurisdictions/* (§6.13) | Declarative data + pure functions | Plugin by registry, Strategy (day counting), Value Object (national IDs) | A new country is a package plus reviewed calendars |
| core/lifecycle (§6.14) | Declarative state machines + pure evaluator | Transition table, guards by id, Specification | One evaluator for every procedure type; every transition testable |
| apps/opportunities (§6.15) | Data model shaped on a public standard | Anti-Corruption Layer per source, idempotent upsert, canonical model (OCDS) | Sources come and go; the model does not |
| core/matching + apps/matching (§6.16) | Pure scoring + database search | Specification (filters), weighted score with explanation | Explainable matches; no extra infrastructure |

**Anti-patterns we avoid:** a general-purpose rules engine [6]; a workflow engine [36]; microservices; a DI container; a repository layer on top of the ORM; event sourcing; EAV tables [35]; one Django app or table set per sector; floats for money; naive datetimes; catching broad exceptions and carrying on; letting the LLM decide anything; storing documents "for convenience".

### 6.12 `sectors/<id>`: sector packs

| | |
|---|---|
| Responsibility | Everything that differs between sectors: resource kinds and their attributes; the cost model for go/no-go; sector document types and their default validity rules; sector warnings (e.g. the taxi fuel risk, §6.6.4) |
| Paradigm | Declarative data (JSON Schemas, CSV) plus pure functions; no Django, no I/O |
| Patterns | Plugin by registry (`shell` registers each pack in the `core/catalog` registry at start-up); Strategy (cost model implements the `CostModel` protocol); JSON Schema per resource kind, with a `schema_version` so stored attributes can be migrated |
| Interface | `SectorPack(id, resource_kinds: dict[str, JsonSchema], cost_model: CostModel, document_types, warnings)` |
| Safety | A pack ships golden tests for its cost model; a tender cannot load if its pack is missing (§6.1). Personal attributes are declared as such in the schema (`"x-personal": true`) so export, erasure and log redaction find them |
| Build | v1: `taxi_student_transport`. Sector #2 is the scalability acceptance test ([`build-plan.md`](build-plan.md) §3) |

### 6.13 `jurisdictions/<cc>`: country packs

| | |
|---|---|
| Responsibility | Everything that differs between countries: public-holiday calendars and day-counting conventions; national ID validators (ΑΦΜ); deductions on public payments (e.g. the 0.12% plus stamp duty of §6.6.2); the national e-procurement platform facts (ΕΣΗΔΗΣ, how it rounds discounts); language of documents |
| Paradigm | Declarative data plus pure functions |
| Patterns | Plugin by registry; Strategy (day counting, holiday computation); Value Object (national IDs) |
| Safety | Calendars are reviewed data per year in `reference/<cc>/` (§6.2); a missing year makes deadlines `ambiguous` |
| Build | v1: `gr`. A second country only with a real client there (v5) |

### 6.14 `core/lifecycle`: procedure types as data

| | |
|---|---|
| Responsibility | The states, transitions and guards of an engagement and of a bid, per procedure type |
| Paradigm | Declarative state machines evaluated by one pure function |
| Patterns | Transition table `{state: {event: (next_state, guard_ids)}}`; guards named by id and implemented once in `core/rules` or `core/pricing` (Specification); no library: a hand-written table is fully inspectable and its tests are table-driven. `python-statemachine` is the upgrade path only if nested or parallel states appear [36] |
| Templates | `dps` (admission, then call-off per invitation; this ΔΣΑ); `open` (one-stage open procedure); `framework` (agreement, then mini-competitions); `negotiated` (short deadlines, often outside the platform, e.g. the 48-hour negotiations of `plan.md` §1); `direct_award` |
| Safety | Each template ships its table-driven tests, including illegal transitions; a guard id that does not resolve makes the template fail to load |
| Build | v1: `dps` and `open`; the others with their first real tender |

### 6.15 `apps/opportunities`: the procurement data model

| | |
|---|---|
| Responsibility | Normalised public procurement data from every source: procedures, lots, items, awards, contracts, buying organisations, document references |
| Paradigm | Relational data model shaped on a public standard |
| Patterns | Canonical model aligned with OCDS 1.1.5 and its lots extension, and with the OCDS-for-eForms mapping [33][34]; Anti-Corruption Layer per source (`kimdis_api`, `diavgeia_api`, `ted_api`), each implementing the `ProcurementSource` port; idempotent upsert keyed on the source's id; CPV 2008 and NUTS as reference data. Only organisations are stored as parties: names of natural persons that appear in award decisions are dropped at the adapter (C1) |
| Safety | Every opportunity keeps its source link and id, so the operator checks the original (S4) |
| Security | Public data only; ingestion rules of §6.8 apply to every adapter |
| Build | v2 |

The CPV vocabulary in force is still the 2008 version: Regulation (EU) 2022/943 only corrected some language versions [44]. The ΚΗΜΔΗΣ API does not publish OCDS today; OCDS alignment is a goal of its redesign [45]. TED API v3 searches eForms notices without an API key [34].

### 6.16 `core/matching` + `apps/matching`: which opportunities fit which client

| | |
|---|---|
| Responsibility | For each client interest profile (CPV prefixes, NUTS regions, value range, sector-pack filters such as vehicle category or capacity), rank new opportunities and explain why each one matched |
| Paradigm | Pure scoring function over value objects (`core/matching`); the candidate search runs in PostgreSQL (`apps/matching`) |
| Patterns | Specification (hard filters: region, category, eligibility facts the client already has); weighted score with a per-term explanation; PostgreSQL full-text search with the built-in `greek` configuration (PostgreSQL 13 and later) plus `pg_trgm` for fuzzy titles [41]; `pgvector` only after a measured recall gap |
| Safety | A match is a suggestion shown to the operator with its reasons; it never starts a bid on its own (S3) |
| Build | v2, when monitoring is sold |

---

## 7. Key flows

**F1. New invitation → client plan (v1, operator-driven).**
1. The operator records the invitation (dates, route table) in the admin. From v2 it arrives through `ingestion`.
2. `core/rules` filters routes (category, base municipality, minimum capacity) and computes deadlines; `core/pricing` computes reference prices.
3. The operator reviews. `documents` renders the client plan, and `alerts` writes the outbox rows and `.ics` events in the same transaction.
4. The client decides. The operator runs the offer validator on the client's intended numbers; the bid reaches `CHECKED` only if the validator is clean and a go/no-go exists.
5. The client submits in ΕΣΗΔΗΣ and reports back; the bid moves to `CLIENT_SUBMITTED`.

**F2. Renewed ΕΕΕΣ request (X1).** The client forwards the ΕΣΗΔΗΣ notification or phones. The operator logs it; `core/rules` computes the 5-working-day deadline conservatively; `alerts` schedules T-3 and T-1 with escalation. Nobody logs into ΕΣΗΔΗΣ for the client.

**F3. Provisional award (X3).** Electronic deadline 10 days after notification, paper originals by the 3rd working day after it (§5.3.1). Checklist R12–R21 with freshness measured against the planned submission date; reminders; guarantee-validity check.

**F4. New tender (v3).** Files → sandboxed parsers → LLM for the rest (two models for requirements) → quote verification → review queue → pull request to `tenders/<id>/` → CI validates the schema → merge → the catalog loads the new version.

---

## 8. Data (v1)

| Table (module) | Key fields | Class | Constraints |
|---|---|---|---|
| client (engagements) | jurisdiction, name, tax_id (ΑΦΜ in Greece), phone, email, retention_until | Personal | (`tenant_id`, `jurisdiction`, `tax_id`) unique; check digit, phone and e-mail validated on every save through the jurisdiction pack (the check digit is not a database CHECK, because the rule differs per country) |
| resource | client, kind (from the sector pack), label, attributes (JSONB), schema_version. Taxi kinds: `vehicle` (plate, category, seats, base municipality), `driver` (display name, licence expiry dates), `escort` (display label, certificate expiry only) | Personal (vehicles, and third parties for staff kinds) | `attributes` valid against the pack's JSON Schema; uniqueness keys declared by the schema (e.g. plate per client); minimum fields only |
| document_record | owner (client or resource), doc_type, issued_on, valid_until, seen_by, seen_at | Personal (metadata) | `valid_until ≥ issued_on` |
| engagement | client, tender_id, tender_version, tender_title, sector, state, admitted_on | Personal | state from the allowed set; transitions only in code |
| bid | engagement, invitation_ref, state, offer_check (validator result per line: route, discount, price, error), gonogo_snapshot, checklist_snapshot | Personal | state from the allowed set (CHECK); the recorded results feed the DRAFT → CHECKED guard |
| acknowledgement | engagement, kind, acknowledged_at | Personal | no free text |
| deadline (alerts) | engagement, step, due_on (the conservative `remind_by`), legal_latest, ambiguous, source_section, acknowledged_at, closed_at | Personal | no personal data in `step`; a saved deadline is not edited (close it and add a new one) |
| outbox (alerts) | idempotency_key, deadline, kind (calendar, T-7, T-3, T-1), due_at, sent_at, attempts, last_error (exception class only) | Internal | `idempotency_key` unique; the recipient is read from the client at send time, so a corrected address is used |
| audit_event (audit) | at, actor, action, object_ref, details | Internal | INSERT-only grant + trigger |
| opportunity, lot, item, award, contract, organisation, document_ref (opportunities, v2) | source, source_id, OCDS-aligned fields, CPV, NUTS, values, dates, sha256 of attachments | Public | (`source`, `source_id`) unique; no natural persons |
| interest_profile (matching, v2) | client, CPV prefixes, NUTS, value range, pack filters | Personal (business profile) | one per client and sector |
| extraction_run, extracted_item (v3) | Run (one per attempt): task, chain step, model and provider that answered, generation id, prompt and schema versions, finish reason, tokens, cost, raw answer. Item: page, quote, quote_verified, found_by, review_status | Public | review transitions only in code |

| Class | Examples | Rule |
|---|---|---|
| Public | Tender documents, notices, route tables | May be sent to the LLM; stored with a hash |
| Internal | Outbox, audit events, cost models | No personal data in logs |
| Personal | Client and driver identity, plates, document metadata, bids | EU-only storage; encryption at rest; access audited; retention schedule |
| **Prohibited** | Document files, criminal-record content, health data, exclusion answers, credentials, signing keys | Never stored anywhere: not in the database, logs, e-mail bodies or backups |

Every table that holds client or operator data carries `tenant_id` from v1 (AD19); with one operator firm it has one value. Row-level security policies on `tenant_id` are enabled in v5, and tests then prove that one tenant's database role cannot read or write another's rows [40].

---

## 9. Deployment (v1)

- One container image ([`Dockerfile`](../Dockerfile): gunicorn for the web, `manage.py` commands for the jobs, non-root, base images pinned by digest; smoke-tested in CI by [`deploy/smoke.sh`](../deploy/smoke.sh)); managed PostgreSQL; a transactional e-mail provider; object storage for public attachments from v2. **All in EU regions, each under a data-processing agreement.**
- The LLM is the one exception to EU hosting (v3): requests go through OpenRouter to zero-data-retention endpoints, EU region first, and carry public tender text only (§6.9, §10.8). The OpenRouter account allows only the chain's models and providers, and each key has a credit limit (`llm-models.md` §6).
- Operators reach the admin only through an identity-aware proxy or VPN with MFA [20]; the app also requires its own login with a second factor (defence in depth, C4).
- **No public endpoints in v1.** Calendar files travel as attachments, so no feed or webhook is exposed.
- Environments: `dev` with synthetic data only (real client data never leaves production); `prod`.
- Backups: the provider's point-in-time recovery plus a nightly encrypted logical dump to a second EU location. A restore is tested every month; a backup that was never restored is not trusted.
- Secrets: the platform's secret store; separate keys per environment; e-mail and LLM keys scoped to their use and rotated.

---

## 10. Security architecture

### 10.1 Trust boundaries and threats (STRIDE)

| Boundary | Main threats | Controls |
|---|---|---|
| TB1 Operator ↔ admin | Spoofing (stolen password); elevation of privilege | Identity-aware proxy + MFA (WebAuthn preferred) [20]; roles; session timeout; audit of views and exports |
| TB2 App ← ΚΗΜΔΗΣ API | Tampering (unexpected payloads); denial of service (huge responses) | TLS verification, host allowlist, shape validation, size caps, timeouts |
| TB3 App ← tender files | Code execution or denial of service through crafted PDF/XLSX | Sandbox with no network, resource limits, patched parsers, `defusedxml` (§6.9) |
| TB4 App ↔ LLM (OpenRouter and the provider behind it) | Prompt injection; invented or missing output; runaway cost; disclosure; routing to a provider that keeps or trains on data | §6.9 controls; public data only; zero-data-retention endpoints; model and provider allowlists; credit and spend limits (`llm-models.md` §6) |
| TB5 App → client e-mail | Spoofing of our identity (phishing) | SPF, DKIM, DMARC `p=reject`; we never ask for credentials; minimum content |
| TB6 Client ↔ operator (phone, e-mail) | Someone impersonates a client to change contact details and divert reminders | Contact changes confirmed by calling back the number on file; audited |
| TB7 App ↔ database, backups | Information disclosure, tampering | Separate database roles; encryption at rest; append-only audit; encrypted backups; restore drills |
| TB8 Developer/CI → production | Supply-chain compromise, leaked secrets | Hash-pinned lockfile, `pip-audit`, Dependabot, secret scanning with push protection [17]; GitHub Actions pinned by commit SHA; branch protection; least-privilege CI tokens |

### 10.2 Identity and access

- Roles: `operator` (client work), `reviewer` (approves tender data and extractions), `admin` (users, retention, erasure). With one person the roles share one account, but the model is ready for four-eyes review when a second person joins.
- A second factor is mandatory (WebAuthn/passkeys preferred, TOTP as fallback) [20]; no shared accounts; one sealed break-glass account. v1: WebAuthn at the identity-aware proxy, and inside the app TOTP through `django-otp` (`OTPAdminSite`), with static codes for the break-glass account. `django-otp-webauthn` (in the sources) would add WebAuthn inside the app; it waits until the proxy is chosen.
- Database roles: `migrator` owns the tables and runs DDL; `app` has only the DML it needs; `app` can only insert into `audit_event`; nobody uses the superuser day to day [21].

### 10.3 Data protection

- TLS everywhere; HSTS; secure, `HttpOnly`, `SameSite` cookies; a Content Security Policy without inline scripts [19].
- Encryption at rest by the managed services. No field-level encryption in v1. That is a deliberate ceiling: revisit it if the database is ever shared with another system or a client portal is added.
- Logs are structured and hold no personal data (a filter redacts ΑΦΜ-like numbers and e-mail addresses); 90-day retention.
- The retention schedule (§10.8) is enforced by `purge_expired`; erasure requests are admin actions and are audited.

### 10.4 Supply chain and CI

- Few dependencies; each one is justified in the `CONTEXT.md` of the module that uses it.
- `uv` lockfile with hashes; `pip-audit` on every CI run; Dependabot; secret scanning with push protection; Actions pinned by commit SHA [17]. Supply-chain failures are A03 in the OWASP Top 10:2025 [12].
- CI gates: tests; import-linter; `ruff` including its security rules; `mypy --strict` on `core/`; `manage.py check --deploy`; the CONTEXT coverage check.

### 10.5 Errors, monitoring, incident response

- Exceptions are never swallowed. A failed job is recorded, retried if idempotent, and alerted. "Mishandling of exceptional conditions" is A10 in the OWASP Top 10:2025 [12].
- Error tracking with personal-data scrubbing (EU-hosted or self-hosted).
- Alerts: missing job heartbeats; repeated ΚΗΜΔΗΣ or LLM failures; outbox backlog.
- Incident runbook: contain; assess the personal-data impact; notify the ΑΠΔΠΧ within 72 hours when required (GDPR Art. 33) and the affected clients when the risk is high (Art. 34) [26].

### 10.6 Standards targets

- OWASP ASVS 5.0 Level 2 for the application [11]. ASVS 5.0 was released on 30 May 2025 and has 17 chapters; Level 2 is intended for applications with logins and personal data.
- OWASP Top 10:2025 as a review checklist [12].
- OWASP Top 10 for LLM Applications 2025 for §6.9 [13].

### 10.7 What we deliberately do not build

A client portal (until v4), file uploads from clients, a document vault, SMS, any integration with ΕΣΗΔΗΣ other than the public OpenData API, any flow that would need a client's credentials.

### 10.8 Privacy and compliance (not legal advice)

| Topic | Position | Source |
|---|---|---|
| Lawful basis | Performance of the service contract, GDPR Art. 6(1)(b), for client, vehicle, driver and document metadata | [24] |
| Criminal-offence data (Art. 10) | Greek Law 4624/2019 Art. 25 lets private bodies process such data only for prosecuting offences or for legal claims; breaches carry criminal penalties (Art. 38). Our purpose fits neither, so **the system never processes it** (AD5). Recording only "client confirmed on date X that they reviewed the exclusion grounds" plausibly falls outside Art. 10 because it records a procedural event, not conviction content: reasoned opinion, to be confirmed by a lawyer | [22] |
| DPIA | Not clearly mandatory on these facts (no Art. 9/10 data, not large scale, no systematic monitoring, no automated decisions with legal effect). Keep a written threshold assessment against Art. 35 and the ΑΠΔΠΧ list (decision 65/2018) anyway, and repeat it before v4 | [23] |
| Records of processing (Art. 30) | The under-250-employees exemption applies only to occasional processing; client processing is our core activity, so **keep a record of processing** | [24] |
| Retention | A written schedule per data class (Art. 5(1)(e)). N months after an engagement closes, set with the lawyer, taking into account the contract length (3 school years) and limitation periods for claims | [24] |
| Transfers | Client personal data stays in the EU. Public tender text sent to the LLM still contains civil servants' names. It passes through OpenRouter (a US company) to Google Vertex AI or Microsoft Azure endpoints, EU region first, with zero data retention (`llm-models.md` §6). The transfer relies on the EU-US Data Privacy Framework (upheld by the General Court in Latombe, T-553/23, 3 Sep 2025; appeal C-703/25 P pending) for certified recipients, and on OpenRouter's data-processing agreement. OpenRouter's own certification and the agreement's wording are UNVERIFIED (§14) | [25] |
| Breach notification | 72 hours to the ΑΠΔΠΧ when required; affected clients when the risk is high | [26] |
| NIS2 (Law 5160/2024) | Unlikely to apply: micro-enterprise, not in a listed sector | [26] |
| Open data reuse | ΚΗΜΔΗΣ OpenData is CC BY 4.0: keep attribution | [28] |

---

## 11. Safety architecture: hazard log

| ID | Hazard | Causes | Controls | Verified by |
|---|---|---|---|---|
| H1 | Deadline missed (X1, X3) | Wrong day counting; missing or moved holiday; job stopped; e-mail not delivered; client ignores it | Conservative `remind_by`; reviewed holiday file; dead man's switch; three channels; escalation to a phone call | Property and golden tests of `deadline()`; monthly alert drill (stop the scheduler, confirm the page) |
| H2 | Wrong or invalid price entered (X2, X5) | Float rounding; decimal discount; above budget; group mismatch | Decimal only; validator blocks; offer-template check; client confirms the numbers | Golden tests from §4.3.2; mutation testing of `core/pricing` |
| H3 | "Ready" shown while a requirement is not met | Missing metadata; stale document; vague rule | Three-valued logic; freshness against the submission date; `manual` rules | Property test: no input renders `UNKNOWN` as satisfied |
| H4 | Outdated tender rules applied | Tender amended; invitation-specific terms | Tender-data version pinned in every result; invitation terms entered and reviewed per invitation; "rules last verified" date shown | Review checklist per invitation |
| H5 | Invented requirement or route (LLM) | Hallucination; prompt injection | Quote verification; dual extraction; human approval; gold-set evaluation | Extraction evaluation before enabling v3 |
| H6 | Wrong client or wrong route | Operator error | Confirmation screens with name and ΑΦΜ digits; route filter shows `§` and source | UI tests |
| H7 | Loss-making contract (X4) | Client underestimates cost or risk | Go/no-go required before `CHECKED`; fuel and cancellation warnings | State-machine guard test |
| H8 | Personal-data breach (X6) | Attack; misconfiguration | §10 | ASVS L2 review; `check --deploy`; restore drill |
| H9 | Client acts on phishing (X7) | Imitation of our e-mails | DMARC reject; no-credentials statement; minimum content | Periodic review of DMARC reports |
| H10 | Reminders stop after a change | Regression | CI gates; smoke test of `send_outbox` and `heartbeat` on synthetic data after every deploy | CI and deploy pipeline |
| H11 | Requirement or route missed by extraction (LLM) | Long-document recall failure; answer cut at `max_tokens`; a fallback model weaker than the primary | Recall-first model choice; dual extraction with the union shown to the reviewer; `length` or empty answer is a failed run; every chain model passes the recall gate (`llm-models.md` §3, §4.4, §7) | Gold-set evaluation: 100% recall in 3 of 3 runs per chain model |

---

## 12. Phases

| Phase | Trigger (`plan.md` §6) | Builds | Gate before go-live |
|---|---|---|---|
| v0 | Now | Spreadsheet + `tenders/` data + manual process | Spreadsheet in an EU-region workspace under a DPA, MFA on, no public sharing links, metadata only (the §8 prohibited list applies to v0 too) |
| v1 | Step 5 gate | core/catalog, core/rules, core/pricing, core/lifecycle, engagements (with resources), alerts, documents (HTML + `.ics`), audit, shell; packs `taxi_student_transport` and `gr` | ASVS L2 self-review of the chapters in use; `check --deploy`; restore drill; record of processing; DPIA threshold assessment |
| v1.1 | Sector #2 is chosen (`plan.md` §6 step 7) | A second sector pack and its tender data only | The scalability acceptance test ([`build-plan.md`](build-plan.md) §3) |
| v2 | Monitoring is sold, or client numbers make manual tracking costly | opportunities, ingestion (ΚΗΜΔΗΣ, Διαύγεια, TED), matching, procrastinate | Rate-limit and attribution review for every source; sandbox in place for attachments; matching precision and recall measured |
| v3 | Onboarding tender #2 by hand costs more than building extraction | extraction (sandbox, LLM, review queue) | Every chain model passes the gold-set evaluation (`llm-models.md` §7); OpenRouter account settings checked (`llm-models.md` §6); LLM Top 10 review |
| v4 | Clients ask for self-service | Client portal | Full ASVS L2 on the public surface; external penetration test; login rate limiting; account-recovery design; new DPIA assessment |
| v5 | A second operator firm, or a client in a second country | Row-level security on `tenant_id`; jurisdiction pack #2 | Cross-tenant access tests fail at the database; data-processing agreements per operator firm; transfer and residency review for the new country |

---

## 13. Verification strategy

| Target | Technique | Gate |
|---|---|---|
| core/rules, core/pricing | Unit tests; property-based tests with Hypothesis [10]; golden tests built from the tender's own rules and examples | 100% branch coverage on these packages; a mutation-score threshold (mutmut [10]): baseline 887/1000 on 2026-09-25, 978 after the tests it prompted; the weekly job fails below 970 (`scripts/mutation.sh`) |
| Engagement and bid state machines | Table-driven tests of every transition, including illegal ones | Every transition covered |
| Adapters | Contract tests against recorded, anonymised fixtures; a live smoke test behind a flag | Fixtures refreshed when the API changes |
| extraction | Evaluation against the gold set (the current tender's `requirements.csv` plus a second tender), 3 runs per model, production settings (`llm-models.md` §7) | 100% recall in every run for each chain model; precision threshold set by the owner before v3 is enabled |
| Security | `check --deploy`, ruff security rules, `pip-audit`, secret scanning, import-linter | CI must pass |
| Operations | Monthly restore drill ([`deploy/restore_drill.sh`](../deploy/restore_drill.sh)); alert drill | Results recorded in the audit log |

---

## 14. Open questions and UNVERIFIED items

| Item | Status | How to close it |
|---|---|---|
| Django 6.2 LTS release date | UNVERIFIED | Check djangoproject.com at v1 start; pick the newest LTS then |
| Regulation 1182/71 day-counting text | Secondary sources only | Read the primary text on EUR-Lex; until then `remind_by` uses the earliest convention (no risk to clients) |
| Moved holidays (e.g. Labour Day 2027 on Holy Saturday) | Unknown until decided | Annual review of `reference/gr/` from the official government announcement |
| ΕΣΗΔΗΣ portal terms on automated access | UNVERIFIED | Irrelevant while we never automate the portal; ask the ΟΠΣ ΕΣΗΔΗΣ helpdesk before anything changes |
| Art. 10 reading of "acknowledged on date X" | Reasoned opinion | Lawyer review before v1 |
| Retention period N | Open | Set with the lawyer (§10.8) |
| Escort documents at the provisional award (R25 medical certificate, R21 declaration) | Reasoned opinion: the v0 workbook records only status and the certificate's expiry date, no names, the same kind of metadata as a driver's licence expiry; whether that date counts as health data (Art. 9) is not settled. The v1 data model has no escort entity | Lawyer review before v1, together with the Art. 10 item |
| OpenRouter's DPA wording, its own log retention and its DPF certification | UNVERIFIED | Read OpenRouter's terms, DPA and privacy policy before v3; low risk while only public text is sent |
| Greek extraction quality of the chain models | UNVERIFIED: no public benchmark covers Greek | Gold-set evaluation (`llm-models.md` §7). The other LLM open items are in `llm-models.md` §8 |
| TED API v3 rate limits; licence of TED notice data for reuse | UNVERIFIED: no numeric limit found; one Publications Office source says CC BY 4.0, not confirmed for API data | Read ted.europa.eu data-reuse terms and measure limits before M10 ([`build-plan.md`](build-plan.md) §4) |
| eCertis REST API: endpoints, authentication, and whether Greek evidence documents are mapped | UNVERIFIED: the API specification exists as a PDF that could not be parsed | Read the specification and query Greek criteria before M15 |
| OCDS 1.2 | UNVERIFIED: 1.1.5 (2020-08-20) is the current release; no dated 1.2 release found | Check standard.open-contracting.org when M9 starts |
| ESPD-EDM 4.1.0 publication date | UNVERIFIED | Check the ESPD-EDM release notes when M1 adds `espd_criterion` |
| New ΟΠΣ ΕΣΗΔΗΣ (Προμηθεύς portal redesigned, live 2026-08-19): public interfaces | UNVERIFIED: no public technical specification found | Re-check before M10; nothing in v1 depends on it |
| Greek article that sets the 100–120 point band for quality-price scoring | UNVERIFIED (practitioner guides cite Law 4412/2016 Art. 86) | Read Art. 86 in the full text [27] before `quality_price_score` is built |

---

## 15. Sources

Research done on 2026-09-23. Secondary sources are marked; the claims resting on them are marked UNVERIFIED in the text where they matter.

**Architecture and patterns**

1. M. Fowler, *MonolithFirst* (2015-06-03). https://martinfowler.com/bliki/MonolithFirst.html
2. K. Westeinde, *Deconstructing the Monolith*, Shopify Engineering (2019-02-21). https://shopify.engineering/deconstructing-monolith-designing-software-maximizes-developer-productivity
3. A. Cockburn, *Hexagonal architecture* (ports and adapters). https://alistair.cockburn.us/hexagonal-architecture
4. G. Bernhardt, *Functional Core, Imperative Shell* (2012). https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell
5. import-linter 2.15 (2026-09-04). https://pypi.org/project/import-linter/ · contract types: https://import-linter.readthedocs.io/en/stable/contract_types.html
6. M. Fowler, *RulesEngine* (2009-01-07). https://martinfowler.com/bliki/RulesEngine.html
7. C. Richardson, *Transactional outbox*. https://microservices.io/patterns/data/transactional-outbox.html
8. Django 6.0 Tasks framework (non-production backends only). https://docs.djangoproject.com/en/6.0/topics/tasks/ · procrastinate: https://github.com/procrastinate-org/procrastinate
9. A. King, *Parse, don't validate* (2019-11-05; direct fetch failed, date corroborated by citing sources). https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/ · M. Fowler, *ValueObject*. https://martinfowler.com/bliki/ValueObject.html
10. Hypothesis. https://github.com/HypothesisWorks/hypothesis · mutmut 3.4.0 (2026-02-22). https://pypi.org/project/mutmut/

**Security**

11. OWASP ASVS 5.0 (released 2025-05-30). https://owasp.org/www-project-application-security-verification-standard/ · summary (secondary): https://softwaremill.com/whats-new-in-asvs-5-0/
12. OWASP Top 10:2025. https://top10.owasp.org/2025/
13. OWASP Top 10 for LLM Applications 2025. https://genai.owasp.org/llmrisk/llm01-prompt-injection/ · https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/
14. pypdf CVE-2025-62707: https://osv.dev/vulnerability/CVE-2025-62707 · CVE-2025-66019: https://www.cvedetails.com/cve/CVE-2025-66019/
15. pdfminer.six CVE-2025-64512 (secondary): https://www.sentinelone.com/vulnerability-database/cve-2025-64512/ · incomplete fix, CVE-2025-70559: https://github.com/advisories/GHSA-f83h-ghpp-7wcc
16. openpyxl XML risks and `defusedxml`: https://github.com/advisories/GHSA-chqf-hx79-gxc6
17. PyPI digital attestations (PEP 740): https://blog.pypi.org/posts/2024-11-14-pypi-now-supports-digital-attestations/ · GitHub push protection by default: https://github.blog/changelog/2024-03-11-secret-scanning-and-push-protection-are-enabled-by-default-on-new-public-repositories/
18. Django 6.0 release (2025-12-03): https://www.djangoproject.com/weblog/2025/dec/03/django-60-released/ · Django 6.1 release (2026-08-05): https://www.djangoproject.com/weblog/2026/aug/05/django-61-released/
19. Django CSP: https://docs.djangoproject.com/en/6.0/ref/csp/ · deployment checklist: https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/
20. django-otp-webauthn: https://github.com/Stormbase/django-otp-webauthn
21. PostgreSQL versioning policy: https://www.postgresql.org/support/versioning/ · row-level security: https://www.postgresql.org/docs/current/ddl-rowsecurity.html · audit trigger: https://wiki.postgresql.org/wiki/Audit_trigger

**Law and compliance**

22. GDPR Art. 10: https://gdpr-info.eu/art-10-gdpr/ · Law 4624/2019 Art. 25: https://www.lawspot.gr/nomikes-plirofories/nomothesia/n-4624-2019/arthro-25-nomos-4624-2019-epexergasia-dedomenon · Art. 38: https://www.lawspot.gr/nomothesia/n-4624-2019/arthro-38-nomos-4624-2019-poinikes-kyroseis/
23. GDPR Art. 35: https://gdpr-info.eu/art-35-gdpr/ · ΑΠΔΠΧ DPIA list: https://www.dpa.gr/sites/default/files/2020-12/article_35_dpia_list_en.pdf
24. GDPR Art. 6: https://gdpr-info.eu/art-6-gdpr/ · Art. 30: https://gdpr-info.eu/art-30-gdpr/
25. Latombe v Commission, T-553/23 (secondary): http://eulawanalysis.blogspot.com/2025/10/the-general-court-of-european-union.html · appeal C-703/25 P (secondary): https://digitalpolicyalert.org/event/35459-latombe-filed-appeal-against-general-court-dismissal-of-challenge-to-european-unionunited-states-data-protection-framework-adequacy-decision-in-latombe-v-commission · public data under GDPR: https://iapp.org/news/a/publicly-available-data-under-gdpr-main-considerations · OpenRouter DPA, Help Center (secondary): https://openrouter.zendesk.com/hc/en-us/articles/47828437697051
26. ΑΠΔΠΧ breach notification: https://www.dpa.gr/el/foreis/asfaleia_dedomenwn/gnwstopoiisi_paraviasis · Law 5160/2024 (NIS2): https://www.ey.com/en_gr/technical/tax/tax-alerts/law-5160-2024-transposition-of-directive-nis-2
27. Law 4412/2016 full text (Art. 60 on time limits): https://eadhsy.gr/n4412/n4412fulltext.html · Regulation 1182/71 (secondary): https://www.europarl.europa.eu/doceo/document//E-8-2017-007700_EN.html · Greek public holidays 2026: https://www.officeholidays.com/countries/greece/2026 · Whit Monday in the public sector: https://www.powergame.gr/ellada/1354670/agiou-pnevmatos-2026-pote-peftei-gia-poious-einai-argia-ti-ischyei-gia-to-dimosio/
28. ΚΗΜΔΗΣ OpenData API help (350 requests/minute, CC BY 4.0): https://cerpp.eprocurement.gov.gr/khmdhs-opendata/help · Swagger: https://cerpp.eprocurement.gov.gr/khmdhs-opendata/swagger-ui/index.html

**Product**

29. OpenRouter documentation (fetched 2026-09-23): provider routing https://openrouter.ai/docs/features/provider-routing · model fallbacks https://openrouter.ai/docs/guides/routing/model-fallbacks · structured outputs https://openrouter.ai/docs/features/structured-outputs · reasoning tokens https://openrouter.ai/docs/guides/best-practices/reasoning-tokens · zero data retention https://openrouter.ai/docs/guides/features/zdr · FAQ (fees) https://openrouter.ai/docs/faq. Model evidence, catalog snapshots and the full source list: [`llm-models.md`](llm-models.md) §9.
30. Διακήρυξη ΔΣΑ Μεταφοράς Μαθητών Μ.Ε. Θεσσαλονίκης, ΑΔΑ ΨΡΘ97ΛΛ-ΕΕΚ (2026-03-06): https://diavgeia.gov.gr/doc/ΨΡΘ97ΛΛ-ΕΕΚ

**Scaling to every sector, procedure and country (research done on 2026-09-24; secondary sources marked)**

31. Plugins in Python (entry points): https://packaging.python.org/guides/creating-and-discovering-plugins/
32. Modular monolith in Django (secondary): https://makimo.com/blog/modular-monolith-in-django/
33. OCDS 1.1.5 release reference: https://standard.open-contracting.org/latest/en/schema/reference/ · OCDS for eForms profile (v1.0.0-rc.1): https://standard.open-contracting.org/profiles/eforms/latest/en/
34. eForms mandatory from 25 Oct 2023: https://docs.ted.europa.eu/eforms-common/FAQ/index.html · eForms SDK releases (1.15.1, 2026-07-20): https://github.com/OP-TED/eForms-SDK/releases · TED API v3: https://docs.ted.europa.eu/api/latest/index.html
35. EAV and JSONB (secondary): https://www.enterprisedb.com/blog/postgresql-anti-patterns-unnecessary-jsonhstore-dynamic-columns · https://coussej.github.io/2016/01/14/Replacing-EAV-with-JSONB-in-PostgreSQL/
36. django-fsm renamed viewflow.fsm (README): https://github.com/viewflow/django-fsm · python-statemachine: https://pypi.org/project/python-statemachine/ · durable workflow engines compared (secondary): https://docs.dbos.dev/why-dbos
37. Directive 2014/24/EU, Art. 67: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32014L0024
38. Law 4412/2016 Art. 90 (uniform discount, works) and Art. 95 (offers): https://eadhsy.gr/n4412/n4412fulltext.html · Art. 90 title: https://www.opengov.gr/ypoian/?p=6115
39. ESPD-EDM (4.1.0): https://docs.ted.europa.eu/ESPD-EDM/latest/index.html · criterion UUIDs kept stable for eCertis: https://github.com/OP-TED/ESPD-EDM/issues/312 · eCertis: https://ec.europa.eu/tools/ecertis/
40. PostgreSQL row-level security: https://www.postgresql.org/docs/current/ddl-rowsecurity.html · django-tenants 3.14.0 (2026-08-05), the schema-per-tenant alternative: https://pypi.org/project/django-tenants/
41. Greek stemming added to PostgreSQL full-text search in 13.0: https://www.postgresql.org/docs/release/13.0/ · pg_trgm: https://www.postgresql.org/docs/current/pgtrgm.html · pgvector: https://github.com/pgvector/pgvector
42. procrastinate 3.10.0 (2026-09-23; periodic tasks, Django integration): https://pypi.org/project/procrastinate/
43. HackSoft Django Styleguide (services and selectors): https://github.com/HackSoftware/Django-Styleguide
44. CPV: Regulation (EC) No 213/2008 and Regulation (EU) 2022/943 (correction of language versions): https://eur-lex.europa.eu/eli/reg/2008/213/oj/eng · https://eur-lex.europa.eu/eli/reg/2022/943
45. ΚΗΜΔΗΣ redesign with OCDS as a goal: https://digitalstrategy.gov.gr/project/kimdis · Διαύγεια OpenData API: https://diavgeia.gov.gr/api/help
