# docs/: CONTEXT

Tender-agnostic strategy and design documents. Anything specific to one tender belongs in `tenders/<id>/`, not here.

| File | Contains / does |
|---|---|
| `plan.md` | Business plan v2 (Greek): changes from v1 (§0), verified market facts (§1), product and responsibility matrix (§2–3), go/no-go cost formula and offer validator rules (§5), roadmap with gates (§6), business-model hypotheses (§8), risks and compliance (§9), next deliverable (§10), sources. §3 (workflow), §4 (requirements) and §7 (architecture) point to their own files instead of repeating them. |
| `architecture.md` | Target architecture (English), safety and security first: decisions AD1–AD12 (§0), drivers and harms (§1), principles (§2), style options and why a modular monolith with ports and adapters and a functional core (§3), stack (§4), module map and dependency rules (§5), each module's paradigm, patterns and controls (§6), key flows (§7), data model and classification (§8), deployment (§9), security architecture incl. STRIDE, access, supply chain, GDPR/Greek-law positions (§10), hazard log (§11), phases v0–v4 (§12), verification (§13), open/UNVERIFIED items (§14), sources (§15). Applies from the v1 gate. |
