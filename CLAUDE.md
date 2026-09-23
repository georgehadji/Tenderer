# CLAUDE.md: Tenderer

Tender-participation support for small professionals (first vertical: taxi → student-transport ΔΣΑ, Thessaloniki).

## 1. Find things through CONTEXT.md (mandatory)

1. Read [`CONTEXT.md`](CONTEXT.md) first. It maps every folder and says where each kind of thing lives.
2. Then read the `CONTEXT.md` of the folder you will work in. It lists every file there and what it does.
3. Do not scan the whole repo when a CONTEXT file can answer the question.

## 2. Keep CONTEXT.md in sync (mandatory, every change)

- Every project folder has a `CONTEXT.md` that describes **every file** in it (other than itself): what it contains and what it does. Tool-state folders that git ignores (e.g. `.claude/claudex/`) are exempt.
- Add, delete, rename or move a file, or change what a file does → update that folder's `CONTEXT.md` **in the same commit**.
- Add, delete or rename a folder → give it a `CONTEXT.md` **and** update the map in the root `CONTEXT.md`.
- A task is not done while any `CONTEXT.md` disagrees with the tree.

## 3. Subagents use Sonnet

- Pass `model: "sonnet"` on every Agent/subagent call. Custom agents in `.claude/agents/` must declare `model: sonnet`.
- Enforced by [`.claude/settings.json`](.claude/settings.json): `CLAUDE_CODE_SUBAGENT_MODEL=sonnet` and `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`, which make every subagent run on Sonnet whatever model a call asks for. Do not remove these settings.

## 4. Modularity and scalability rules

- **The core is tender-agnostic. Each tender is a self-contained module** under `tenders/<id>/`, with `sop.md` and `requirements.csv`. A new tender, region or vertical = a new folder. The core does not change.
- **Single source of truth.** Each fact lives in one file and every other file links to it. Requirements live only in `requirements.csv`, and the strategy lives only in `docs/plan.md`.
- **Data contract.** The `requirements.csv` schema is defined in [`tenders/CONTEXT.md`](tenders/CONTEXT.md). Change the schema only together with that file and every existing tender.
- **Sources.** Every claim about a tender cites its `§` in the source document. A claim without a source is a hypothesis and must be labelled as one.
- **Code.** Do not write any before the gate in `docs/plan.md` §6 step 5. After that, follow [`docs/architecture.md`](docs/architecture.md): the folder layout (§5.4), the dependency rules checked by import-linter (§5.2–5.3), and each module's paradigm, patterns and controls (§6). Each module folder has its own `CONTEXT.md`. Modules depend on data contracts and each other's `api.py`, not on internals. Build only what a real client cycle needs (YAGNI).
- **Safety and security come first.** A change that touches deadlines, money, eligibility, personal data or external input must keep the principles and controls of `docs/architecture.md` §2, §10 and §11. If it cannot, update that document in the same change and say why.

## 5. Product invariants (never build against these)

- Never handle a client's credentials (Taxisnet, ΕΣΗΔΗΣ). Never sign or submit on the client's behalf.
- Never store sensitive documents (criminal record, health). Store metadata only (type, issue date, expiry).
- The tool shows numbers. The client decides the discount.

## 6. Conventions

- Business and domain docs are written in Greek. Code, identifiers, paths, technical design docs (`docs/architecture.md`, `docs/llm-models.md`), `CONTEXT.md`/`CLAUDE.md` and commit messages are written in English.
