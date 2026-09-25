# src/tenderer/core/catalog/: CONTEXT

Loads `tenders/<id>/` into frozen objects, or refuses the whole tender (fail closed, S1). Data contract: [`tenders/CONTEXT.md`](../../../../tenders/CONTEXT.md). Built in M1 (2026-09-24).

| File | Contains / does |
|---|---|
| `tender.py` | `load_tender(dir, packs, commit) -> Tender`. Parses `tender.toml` (stdlib `tomllib`; rates as decimal strings, never TOML floats) and `requirements.csv` schema v2; collects every problem with its line and column into one `TenderLoadError`. Types: `Tender`, `Requirement`, `Validity` (`ValidityKind`, `Unit`, `Anchor`), `OfferTerms`. `Tender.version` = first 12 characters of the git commit + SHA-256 of both files (S4). |
| `packs.py` | Pack contracts `SectorPack` (with `labels`: client-facing text of its cost lines and warnings; and `gonogo`: the sector's go/no-go of one route from plain values, so apps reach a cost model through the registry) and `JurisdictionPack` (frozen dataclasses) and the `Packs` registry. Core never imports a pack; `shell/packs.py` fills the registry and passes it in. |
