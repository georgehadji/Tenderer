# tenders/: CONTEXT

One folder per tender (or ΔΣΑ). Each folder is a self-contained module. Adding a tender, region or vertical means adding a folder here; nothing else changes.

## Tender modules

| Folder | Tender |
|---|---|
| [`pkm-meth-student-transport-dsa-2026/`](pkm-meth-student-transport-dsa-2026/CONTEXT.md) | ΔΣΑ Μεταφοράς Μαθητών Μ.Ε. Θεσσαλονίκης 2026–2029 (ΠΚΜ), ΑΔΑ ΨΡΘ97ΛΛ-ΕΕΚ, category Β (Ε.Δ.Χ.) |

## Module contract (every tender folder has these files)

| File | Required | Contains |
|---|---|---|
| `CONTEXT.md` | yes | Source identifiers (ΑΔΑ, ΚΗΜΔΗΣ ref, date, links) and the file list |
| `sop.md` | yes | Step-by-step workflow (Greek). Every step cites `§` of the source document |
| `requirements.csv` | yes | One row per requirement/document, in the schema below |

Folder name: `<authority>-<area>-<subject>-<procedure>-<year>`, lowercase ASCII, hyphen-separated.

## `requirements.csv` schema (data contract)

UTF-8, comma-separated, header row required. Future code reads this file as the `requirements` table, so change it only as `CLAUDE.md` §4 describes.

| Column | Meaning | Example |
|---|---|---|
| `id` | Stable ID, unique within the tender | `R12` |
| `requirement` | What is needed (Greek) | `Απόσπασμα ποινικού μητρώου` |
| `stage` | Workflow step in `sop.md` when it is needed (comma-separated if several) | `Β9` |
| `issuer` | Who issues or provides it | `gov.gr` |
| `validity` | Validity or freshness rule, relative to the submission date | `≤3 μήνες πριν την υποβολή` |
| `source_section` | `§` in the source document | `5.3.2 α1` |
