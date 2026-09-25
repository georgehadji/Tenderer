# src/tenderer/apps/documents/templates/documents/: CONTEXT

| File | Contains / does |
|---|---|
| `client_plan.html` | The client plan as an e-mail-safe HTML page (inline styles, tables): 1. deadlines, 2. documents with status and `§`, 3. go/no-go per route (reference price, cost lines, what remains per day without discount, the largest discount without loss, warnings) with the line that the client decides the discount, 4. draft declarations between two watermarks, then the never-ask line. Auto-escaping is on for every value. |
