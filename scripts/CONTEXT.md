# scripts/: CONTEXT

| File | Contains / does |
|---|---|
| `check_context.py` | `CLAUDE.md` §2 as a CI gate: every folder with tracked files has a `CONTEXT.md` that names each file (package markers exempt), and the root `CONTEXT.md` names every folder. Exit 1 on any gap. |
