# src/tenderer/apps/v0import/management/commands/: CONTEXT

| File | Contains / does |
|---|---|
| `import_v0.py` | `manage.py import_v0 <file.xlsx> --client <id> --tender <id> [--accept-differences]`: runs the import in one correlation scope and prints the reconciliation report (`same`, `DIFF`, `note` lines and the count of differences). Exits non-zero, with nothing imported, on any difference or unreadable file. |
