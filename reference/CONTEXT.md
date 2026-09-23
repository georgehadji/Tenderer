# reference/: CONTEXT

Dated snapshots of external reference data that design decisions rely on. Snapshots are never edited by hand; a refresh adds new dated files and the decision documents are re-checked against them.

| File | Contains / does |
|---|---|
| `openrouter-models-2026-09-23.csv` | Snapshot of the OpenRouter model catalog (455 models) taken 2026-09-23 from `GET https://openrouter.ai/api/v1/models` (public, no key needed). One row per model id: name, release date, context length, max output tokens, prices in USD per 1M tokens (prompt, completion, cache read), input modalities, flags for `structured_outputs` / `response_format` / `tools` / `reasoning` support, Artificial Analysis intelligence / coding / agentic index as published in the catalog, knowledge cutoff, expiration date. Input to the model choice in [`docs/llm-models.md`](../docs/llm-models.md) §1–§2. |
| `openrouter-endpoints-2026-09-23.csv` | Snapshot of the OpenRouter endpoints of the 14 candidate models of [`docs/llm-models.md`](../docs/llm-models.md) §2 (177 rows), taken 2026-09-23 from `GET https://openrouter.ai/api/v1/models/{author}/{slug}/endpoints` and joined with the zero-data-retention list `GET https://openrouter.ai/api/v1/endpoints/zdr` (both public, no key needed). One row per endpoint: model id, endpoint tag (provider and region, e.g. `google-vertex/europe`), provider name, model snapshot (e.g. `anthropic/claude-opus-5.5-20260921`), quantization, 1/0 flags for ZDR and for `structured_outputs` / `response_format` / `reasoning` / `temperature` / `top_p` / `seed` support, prices in USD per 1M tokens, max output tokens. Evidence for the endpoint choice (`docs/llm-models.md` §2, §4.2) and the sampling settings (§5). |

**Refresh** at least quarterly, and whenever a model in a fallback chain gets an `expiration_date` or a new snapshot:

1. Catalog: fetch the same URL and write a new `openrouter-models-<YYYY-MM-DD>.csv` with the same columns (prices are the catalog's per-token prices × 1,000,000; flags are 1/0 from `supported_parameters`).
2. Endpoints: fetch the endpoints of every candidate in `docs/llm-models.md` §2, set `zdr` to 1 when the pair (model id, endpoint tag) is on the ZDR list, and write a new `openrouter-endpoints-<YYYY-MM-DD>.csv` with the same columns.
3. List the new files in the table above, then follow `docs/llm-models.md` §8.
