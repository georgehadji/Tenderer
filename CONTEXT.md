# CONTEXT: repository map

Start here. Each folder has its own `CONTEXT.md` that lists its files. Rules for keeping these files in sync: [`CLAUDE.md`](CLAUDE.md) §2.

## Tree

```
/
├── CLAUDE.md            agent rules (navigation, CONTEXT sync, Sonnet subagents, modularity)
├── CONTEXT.md           this map
├── .gitignore           keeps local tool state out of git
├── .claude/             Claude Code project settings        → .claude/CONTEXT.md
├── docs/                business plan and architecture       → docs/CONTEXT.md
└── tenders/             one self-contained module per tender → tenders/CONTEXT.md
    └── pkm-meth-student-transport-dsa-2026/                   → tenders/pkm-meth-student-transport-dsa-2026/CONTEXT.md
```

## Where to find…

| Looking for | Go to |
|---|---|
| Agent rules, conventions, product invariants | [`CLAUDE.md`](CLAUDE.md) |
| Business plan, market facts, go/no-go formula, roadmap and gates, risks | [`docs/plan.md`](docs/plan.md) |
| Architecture: style, stack, module map and dependency rules, paradigm and patterns per module | [`docs/architecture.md`](docs/architecture.md) §3–§6 |
| Security (threat model, access, supply chain, GDPR positions) and safety (hazard log) design | [`docs/architecture.md`](docs/architecture.md) §10–§11 |
| Build phases v0–v4 and what each needs before go-live | [`docs/architecture.md`](docs/architecture.md) §12 |
| How tender modules are structured; `requirements.csv` schema | [`tenders/CONTEXT.md`](tenders/CONTEXT.md) |
| Step-by-step workflow for the Thessaloniki student-transport ΔΣΑ (taxi) | [`tenders/pkm-meth-student-transport-dsa-2026/sop.md`](tenders/pkm-meth-student-transport-dsa-2026/sop.md) |
| Document and requirement checklist for that tender (R1–R23) | [`tenders/pkm-meth-student-transport-dsa-2026/requirements.csv`](tenders/pkm-meth-student-transport-dsa-2026/requirements.csv) |
| Subagent model enforcement (Sonnet) | [`.claude/settings.json`](.claude/settings.json) |

## Folder index

| Folder | CONTEXT file | Purpose |
|---|---|---|
| `.claude/` | [`.claude/CONTEXT.md`](.claude/CONTEXT.md) | Claude Code project settings shared through git |
| `docs/` | [`docs/CONTEXT.md`](docs/CONTEXT.md) | Tender-agnostic strategy, planning and architecture documents |
| `tenders/` | [`tenders/CONTEXT.md`](tenders/CONTEXT.md) | Tender modules and their shared data contract |
| `tenders/pkm-meth-student-transport-dsa-2026/` | [`CONTEXT.md`](tenders/pkm-meth-student-transport-dsa-2026/CONTEXT.md) | ΔΣΑ Μεταφοράς Μαθητών Μ.Ε. Θεσσαλονίκης 2026–2029, category Β (Ε.Δ.Χ.) |
