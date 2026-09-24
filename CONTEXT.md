# CONTEXT: repository map

Start here. Each folder has its own `CONTEXT.md` that lists its files. Rules for keeping these files in sync: [`CLAUDE.md`](CLAUDE.md) §2.

## Tree

```
/
├── CLAUDE.md            agent rules (navigation, CONTEXT sync, Sonnet 5 subagents, modularity)
├── CONTEXT.md           this map
├── .gitignore           keeps local tool state, private interview data and Python build output out of git
├── .python-version      Python version for uv (3.14)
├── pyproject.toml       package, dependencies, and the settings of ruff, mypy, pytest, coverage, import-linter
├── uv.lock              hash-pinned lockfile (never edit by hand: `uv lock`)
├── manage.py            Django entry point (settings: tenderer.shell.settings)
├── compose.yaml         development PostgreSQL 17 (synthetic data only)
├── .claude/             Claude Code project settings        → .claude/CONTEXT.md
├── .github/workflows/   CI: every gate of build-plan M0      → .github/workflows/CONTEXT.md
├── discovery/           customer discovery (plan steps 2–4)  → discovery/CONTEXT.md
├── docs/                plan, architecture, build plan, LLMs → docs/CONTEXT.md
├── reference/           dated snapshots of external data     → reference/CONTEXT.md
│   └── gr/              Greek holiday calendars per year     → reference/gr/CONTEXT.md
├── scripts/             repository checks                    → scripts/CONTEXT.md
├── src/tenderer/        the application package              → src/tenderer/CONTEXT.md
│   ├── core/            pure core                            → src/tenderer/core/CONTEXT.md
│   │   ├── catalog/     tenders as typed data, pack contracts → src/tenderer/core/catalog/CONTEXT.md
│   │   ├── rules/       checklists, deadlines                → src/tenderer/core/rules/CONTEXT.md
│   │   └── pricing/     money, offer validator, go/no-go     → src/tenderer/core/pricing/CONTEXT.md
│   ├── sectors/         sector packs                         → src/tenderer/sectors/CONTEXT.md
│   │   └── taxi_student_transport/                            → src/tenderer/sectors/taxi_student_transport/CONTEXT.md
│   ├── jurisdictions/   country packs                        → src/tenderer/jurisdictions/CONTEXT.md
│   │   └── gr/          Greece                               → src/tenderer/jurisdictions/gr/CONTEXT.md
│   └── shell/           Django project, pack registry        → src/tenderer/shell/CONTEXT.md
├── tests/               one test file per module             → tests/CONTEXT.md
└── tenders/             one self-contained module per tender → tenders/CONTEXT.md
    └── pkm-meth-student-transport-dsa-2026/                   → tenders/pkm-meth-student-transport-dsa-2026/CONTEXT.md
```

**Run the checks locally** (the same gates as CI): `uv sync`, then `uv run pytest`, `uv run ruff check .`, `uv run mypy`, `uv run lint-imports`, `uv run python scripts/check_context.py`.

## Where to find…

| Looking for | Go to |
|---|---|
| Agent rules, conventions, product invariants | [`CLAUDE.md`](CLAUDE.md) |
| Business plan, market facts, go/no-go formula, roadmap and gates, risks | [`docs/plan.md`](docs/plan.md) |
| Architecture: style, stack, module map and dependency rules, paradigm and patterns per module | [`docs/architecture.md`](docs/architecture.md) §3–§6 |
| Security (threat model, access, supply chain, GDPR positions) and safety (hazard log) design | [`docs/architecture.md`](docs/architecture.md) §10–§11 |
| Build phases v0–v5 and what each needs before go-live | [`docs/architecture.md`](docs/architecture.md) §12 |
| How the code scales to every sector, procedure type and country (packs, offer shapes, lifecycles, OCDS-shaped data) | [`docs/architecture.md`](docs/architecture.md) §5.5, §6.12–§6.16 |
| Build order of the whole codebase: milestones, acceptance criteria, effort guesses | [`docs/build-plan.md`](docs/build-plan.md) |
| LLM use: models per task, fallback chains, OpenRouter request settings (routing, reasoning, temperature), evaluation gate | [`docs/llm-models.md`](docs/llm-models.md) |
| OpenRouter model catalog and endpoint snapshots (prices, capabilities, zero data retention) | [`reference/CONTEXT.md`](reference/CONTEXT.md) |
| How tender modules are structured; `requirements.csv` schema | [`tenders/CONTEXT.md`](tenders/CONTEXT.md) |
| Step-by-step workflow for the Thessaloniki student-transport ΔΣΑ (taxi) | [`tenders/pkm-meth-student-transport-dsa-2026/sop.md`](tenders/pkm-meth-student-transport-dsa-2026/sop.md) |
| Document and requirement checklist for that tender (R1–R26) | [`tenders/pkm-meth-student-transport-dsa-2026/requirements.csv`](tenders/pkm-meth-student-transport-dsa-2026/requirements.csv) |
| Desk research (plan step 1): 2026 taxi invitations, routes, outcomes, the previous ΔΣΑ 2023–2026 (offers, barren routes, winning discounts), ΔΣΑ registry, proposed gate N | [`tenders/pkm-meth-student-transport-dsa-2026/desk-research-2026.md`](tenders/pkm-meth-student-transport-dsa-2026/desk-research-2026.md) |
| Interview kit (plan step 2): who to interview, channels, consent, questions, how the gate is measured | [`discovery/interviews-taxi-2026.md`](discovery/interviews-taxi-2026.md) |
| Concierge kit (plan step 3): meetings, what we record and never record, templates, record of processing; draft pilot agreement | [`discovery/concierge-phase-a-2026.md`](discovery/concierge-phase-a-2026.md) · [`discovery/pilot-agreement-draft.md`](discovery/pilot-agreement-draft.md) |
| Concierge kit (plan step 4): invitation cycle, go/no-go meeting, pre-submission check; the go/no-go calculator, offer validator and Phase B document checklist spreadsheet | [`discovery/concierge-phase-b-2026.md`](discovery/concierge-phase-b-2026.md) · [`discovery/concierge-phase-b-workbook.xlsx`](discovery/concierge-phase-b-workbook.xlsx) |
| Subagent model enforcement (Sonnet 5) | [`.claude/settings.json`](.claude/settings.json) |
| Code: what is built so far (M0–M3: catalog, rules, pricing, GR and taxi packs, Django shell) | [`src/tenderer/CONTEXT.md`](src/tenderer/CONTEXT.md) and [`docs/build-plan.md`](docs/build-plan.md) §2 |
| Tender manifest (`tender.toml`) and `requirements.csv` schema v2 | [`tenders/CONTEXT.md`](tenders/CONTEXT.md) |
| Greek holiday calendars and how to review them | [`reference/gr/CONTEXT.md`](reference/gr/CONTEXT.md) |
| CI gates | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) |

## Folder index

| Folder | CONTEXT file | Purpose |
|---|---|---|
| `.claude/` | [`.claude/CONTEXT.md`](.claude/CONTEXT.md) | Claude Code project settings shared through git |
| `discovery/` | [`discovery/CONTEXT.md`](discovery/CONTEXT.md) | Customer discovery for the plan's gates: interview kit, concierge kits for Phases A and B, templates, spreadsheet, draft pilot agreement (filled data stays in the git-ignored `discovery/private/`) |
| `docs/` | [`docs/CONTEXT.md`](docs/CONTEXT.md) | Tender-agnostic strategy, planning, architecture and LLM-choice documents |
| `.github/workflows/` | [`.github/workflows/CONTEXT.md`](.github/workflows/CONTEXT.md) | CI workflow |
| `reference/` | [`reference/CONTEXT.md`](reference/CONTEXT.md) | Dated snapshots of external reference data (OpenRouter model catalog and endpoints) |
| `reference/gr/` | [`reference/gr/CONTEXT.md`](reference/gr/CONTEXT.md) | Greek public holidays per year, with review status |
| `scripts/` | [`scripts/CONTEXT.md`](scripts/CONTEXT.md) | Repository checks run by CI |
| `src/tenderer/` | [`src/tenderer/CONTEXT.md`](src/tenderer/CONTEXT.md) | Application package; each subfolder below has its own `CONTEXT.md` |
| `src/tenderer/core/`, `src/tenderer/core/catalog/`, `src/tenderer/core/rules/`, `src/tenderer/core/pricing/` | one per folder | Pure core modules |
| `src/tenderer/sectors/`, `src/tenderer/sectors/taxi_student_transport/` | one per folder | Sector packs |
| `src/tenderer/jurisdictions/`, `src/tenderer/jurisdictions/gr/` | one per folder | Country packs |
| `src/tenderer/shell/` | [`src/tenderer/shell/CONTEXT.md`](src/tenderer/shell/CONTEXT.md) | Django project and pack registry |
| `tests/` | [`tests/CONTEXT.md`](tests/CONTEXT.md) | Tests, one file per module |
| `tenders/` | [`tenders/CONTEXT.md`](tenders/CONTEXT.md) | Tender modules and their shared data contract |
| `tenders/pkm-meth-student-transport-dsa-2026/` | [`CONTEXT.md`](tenders/pkm-meth-student-transport-dsa-2026/CONTEXT.md) | ΔΣΑ Μεταφοράς Μαθητών Μ.Ε. Θεσσαλονίκης 2026–2029, category Β (Ε.Δ.Χ.) |
