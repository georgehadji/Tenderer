# scripts/: CONTEXT

| File | Contains / does |
|---|---|
| `mutation.sh` | Mutation testing of `core/pricing` and `core/rules` with mutmut 3, in a throwaway Linux container fed only git-tracked files (never `discovery/`). Prints the tally, the score per 1000 mutants and the diff of every survivor; `MIN_SCORE` makes it fail below a threshold. Configuration: `[tool.mutmut]` in `pyproject.toml`. Baseline 887 on 2026-09-25, 978 after the tests it prompted. |
| `check_context.py` | `CLAUDE.md` §2 as a CI gate: every folder with tracked files has a `CONTEXT.md` that names each file (package markers exempt), and the root `CONTEXT.md` names every folder. Exit 1 on any gap. |
