# tenders/: CONTEXT

One folder per tender (or ΔΣΑ). Each folder is a self-contained module. Adding a tender, region or vertical means adding a folder here; nothing else changes.

## Tender modules

| Folder | Tender |
|---|---|
| [`pkm-meth-student-transport-dsa-2026/`](pkm-meth-student-transport-dsa-2026/CONTEXT.md) | ΔΣΑ Μεταφοράς Μαθητών Μ.Ε. Θεσσαλονίκης 2026–2029 (ΠΚΜ), ΑΔΑ ΨΡΘ97ΛΛ-ΕΕΚ, category Β (Ε.Δ.Χ.) |

## Module contract (every tender folder has the required files)

| File | Required | Contains |
|---|---|---|
| `CONTEXT.md` | yes | Source identifiers (ΑΔΑ, ΚΗΜΔΗΣ ref, date, links) and the file list |
| `tender.toml` | yes | Manifest read by `core/catalog` (schema below) |
| `sop.md` | yes | Step-by-step workflow (Greek). Every step cites `§` of the source document |
| `requirements.csv` | yes | One row per requirement/document, in the schema below |
| `declarations/<requirement id>.txt` | no | Draft text of a declaration without sensitive parts, rendered into the client plan by `apps/documents` (variables in the folder's `CONTEXT.md`) |
| `desk-research-<year>.md` | no | Market numbers for the tender (Greek): invitations, routes, outcomes, with sources |
| `routes-<category>-<year>.csv` | no | Route tables extracted from invitations. Research data, not a data contract: code must not read it until a schema is defined here |
| `awards-<category>-<years>.csv` | no | Per-route outcomes from published award decisions: reference price, winning discount or barren. Research data, not a data contract, same rule as above. Never names of natural persons |

Folder name: `<authority>-<area>-<subject>-<procedure>-<year>`, lowercase ASCII, hyphen-separated.

## `tender.toml` schema (data contract, schema version 2)

Read by `src/tenderer/core/catalog/tender.py`. The tender does not load if any key is missing or invalid, or if a pack, lifecycle or offer shape is not registered in `src/tenderer/shell/packs.py`.

| Key | Meaning | Example |
|---|---|---|
| `schema_version` | Must be `2` | `2` |
| `id`, `title` | Folder name; human title (Greek) | |
| `sector` | Sector pack id (`src/tenderer/sectors/`) | `taxi_student_transport` |
| `jurisdiction` | Jurisdiction pack id (`src/tenderer/jurisdictions/`) | `gr` |
| `lifecycle` | Procedure template (`docs/architecture.md` §6.14) | `dps` |
| `offer_shape` | One of the closed set of `docs/architecture.md` §6.3 | `discount_on_reference` |
| `[sources]` | Identifiers of the source documents | `ada = "ΨΡΘ97ΛΛ-ΕΕΚ"` |
| `[offer]` | `offer_validity_months`, `participation_guarantee_extra_days`, `performance_guarantee_extra_months` (integers); `participation_guarantee_rate`, `performance_guarantee_rate` (**decimal strings**, e.g. `"0.002"`, because TOML floats are binary) | |

## `requirements.csv` schema (data contract, schema version 2)

UTF-8, comma-separated, header row required, columns in this order. `core/catalog` reads it; change it only as `CLAUDE.md` §4 describes. Any invalid row makes the whole tender fail to load, with the line and column named.

| Column | Meaning | Example (R12) |
|---|---|---|
| `id` | Stable ID `R<number>`, unique within the tender | `R12` |
| `requirement` | What is needed (Greek) | `Απόσπασμα ποινικού μητρώου` |
| `stage` | Workflow step in `sop.md` when it is needed (several allowed; codes such as `Β9` are read, other text is ignored) | `Β9` |
| `issuer` | Who issues or provides it | `gov.gr` |
| `validity` | Validity or freshness rule in words (Greek); the machine columns below encode it | `≤3 μήνες πριν την υποβολή` |
| `source_section` | `§` in the source document | `5.3.2 α1` |
| `doc_type` | Stable key that joins to document metadata; must be a document type of the tender's sector or jurisdiction pack | `criminal_record_extract` |
| `applies_to` | `client`, `offer`, `engagement` or a resource kind of the sector pack; comma-separated if several | `client` |
| `validity_kind` | `in_force` (valid on the anchor date), `issued_within` (issued inside the window of amount + unit that ends on the anchor), `signed_after` (after the anchor and not after the submission), `valid_until` (valid until anchor + amount), `none` (a record is enough), `manual` (the tender is vague; an operator decides) | `issued_within` |
| `validity_amount`, `validity_unit` | Positive integer and `days`, `working_days` or `months`; only for `issued_within` and `valid_until` (`valid_until` takes no `working_days`) | `3`, `months` |
| `validity_anchor` | `submission` (the planned submission of the stage being checked), `invitation_sent`, `offer_validity_end`, `contract_end`; empty for `none` and `manual` | `submission` |
| `espd_criterion` | ESPD criterion UUID (AD18) when the requirement is an exclusion or selection criterion; empty otherwise. Empty for every row today: the UUIDs are not yet verified against ESPD-EDM | empty |
