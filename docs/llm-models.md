# LLM models through OpenRouter: choice, fallbacks, request settings

| | |
|---|---|
| Status | Proposed. Applies from v3 ([`architecture.md`](architecture.md) §12), when `apps/extraction` is built. |
| Date | 2026-09-23 |
| Owns | Which model each LLM task uses and in what fallback order; the OpenRouter request settings (routing, reasoning, sampling); the evaluation gate for models; the refresh procedure. |
| Does not own | The extraction pipeline and its controls ([`architecture.md`](architecture.md) §6.9); privacy positions ([`architecture.md`](architecture.md) §10.8); the catalog data ([`reference/`](../reference/CONTEXT.md)). |

Numbers in square brackets point to §9 (Sources). **UNVERIFIED** marks a claim not confirmed against a primary source. Prices are OpenRouter list prices in USD per million tokens on 2026-09-23 [1].

---

## 0. Decisions on one page

| ID | Decision | Main reason |
|---|---|---|
| M1 | **Every LLM call goes through OpenRouter**, from one adapter (`adapters/llm_openrouter`) that posts JSON with `httpx` | One integration reaches Anthropic, OpenAI and Google models, so one vendor's outage or failed evaluation does not stop extraction. Privacy routing is set per request. Model prices equal the vendors' own; OpenRouter charges 5.5% on credit purchases [2] |
| M2 | **Accuracy first; price only breaks ties** | At our volume the whole LLM bill stays under about $20 a month on the most accurate models (§1.4). A cheaper model saves little and adds the risk of a missed requirement |
| M3 | **Requirements (T1) are extracted by two models from different vendors on every tender**, and the reviewer sees the union | The quote check catches invented values but not omissions. A second, independent extraction is the cheapest control for omissions: about $0.60 more per tender |
| M4 | **Our code runs the fallback chain**, not OpenRouter's `models` array | OpenRouter falls back only on errors [3]. An answer that ends with `length`, is empty or fails our schema must also move to the next model, and each model needs its own provider and reasoning settings |
| M5 | **Every request is pinned to zero-data-retention (ZDR) endpoints, EU region first**, with `require_parameters: true` and `data_collection: "deny"` | Public tender text still contains civil servants' names ([`architecture.md`](architecture.md) §10.8). Only endpoints that keep nothing and support every parameter we send may see it [4][5] |
| M6 | **Reasoning on, reasoning text excluded, room for it in `max_tokens`.** An answer cut at `length`, or an empty one, is a failed run | Reasoning tokens are billed as output and count against `max_tokens`; an exhausted budget returns no answer and is still billed [6] |
| M7 | **No `temperature`, `top_p`, `top_k` or `seed` on any call**; in effect every call runs at temperature 1 | Claude accepts only 1.0, GPT-6 does not accept them while reasoning and runs at its default of 1, and Google recommends Gemini's default of 1.0. None of the chosen endpoints accepts them, so with `require_parameters` no endpoint would be left (§5) |
| M8 | **A model enters a chain only after passing the gold-set evaluation** with the exact production settings | No public benchmark covers Greek tender extraction (§2) |

---

## 1. Selection method (value for money)

### 1.1 Tasks

| Task | What | Input | Output | Risk |
|---|---|---|---|---|
| T1 | Requirements extraction: every eligibility requirement, document, deadline and guarantee in a tender document, as candidate rows for `requirements.csv` | Page-marked text of the whole document. Assumed 120k tokens: the current διακήρυξη [7] has 219,853 characters of text; the evaluation measures the real count | JSON of about 12k tokens, plus up to about 24k reasoning tokens | Safety-critical: a missed or wrong requirement can cost the client the contract (`architecture.md` §1.2) |
| T2 | Table extraction: route and price tables that the deterministic parsers cannot read (`architecture.md` §6.9 step 2) | Text of the table pages, about 30k tokens | JSON rows, about 10k tokens including reasoning | High, but every row carries a checked quote and is reviewed |

A cheap triage task ("is this notice relevant?") is not needed: notices are filtered by CPV code and contracting authority, deterministically (`architecture.md` §6.8). Add one when ingestion volume makes manual triage costly.

### 1.2 Filters

Applied to the 455 models of the catalog snapshot [1]:

1. Supports `structured_outputs` and `response_format` (strict JSON Schema).
2. Has at least one endpoint that is on OpenRouter's ZDR list [5] **and** supports strict structured outputs [1].
3. Has no `expiration_date`. For example, the `google/gemini-2.5-*` models expire on 2026-10-20.
4. Paid variant. `:free` variants have their own data-training settings and daily request caps [8].
5. Context window of at least 200k tokens. Every remaining candidate has 500k or more.

### 1.3 Ranking: recall first

The quote check (`architecture.md` §6.9 step 4) rejects any value whose quote does not occur on its page, so an invented value cannot reach the reviewer unflagged. It cannot notice a requirement that was never extracted. Candidates are therefore ranked by:

1. **Long-document recall**, proxied by Artificial Analysis AA-LCR, a long-context reasoning benchmark over document sets of about 100k tokens [9].
2. **General reasoning**: the Artificial Analysis Intelligence Index as published in the catalog [1].
3. **Tie-breaker and exclusion filter**: the AA-Omniscience hallucination rate, the share of wrong answers given instead of an abstention [9]. It is measured without a supplied document, so it is a weak proxy for faithfulness to one. It is used only to exclude extreme values.

No benchmark measures Greek. No Greek result was found for any candidate, so Greek quality is **UNVERIFIED for every model**. The gold-set evaluation (§7) is the real test.

### 1.4 Cost at our volume

Cost of one T1 run = 120k × input price + 36k × output price (12k answer + 24k reasoning). Worst case: the run uses the whole `max_tokens` of §4.2.

| Item | Typical | Worst case |
|---|---|---|
| T1 dual extraction per tender (Opus 5.5 + GPT-6 Sol) | $1.80 | $3.60 |
| T2 per table job (Gemini 3.8 Flash) | $0.06 | $0.08 |
| One evaluation round (3 T1 models × 3 runs × 2 gold tenders) | about $12 | about $24 |

With up to 5 new tenders a month (a generous assumption for v3), production cost stays under $20 a month.

The intelligence/cost frontier of the snapshot, at 120k input and 12k output without reasoning [1]:

| Model | Intelligence Index | $ per job |
|---|---|---|
| `nvidia/nemotron-3-nano-30b-a3b` | 8.9 | 0.0084 |
| `openai/gpt-6-luna:batch` | 37.3 | 0.0090 |
| `z-ai/glm-5.3-flash:batch` | 41.8 | 0.0096 |
| `xiaomi/mimo-v2.6-pro` | 46.3 | 0.0626 |
| `openai/gpt-6-sol:batch` | 47.5 | 0.18 |
| `anthropic/claude-opus-5.5:batch` | 57.6 | 0.36 |

Every frontier model below Opus 5.5 saves at most about $1 per tender, and each fails a filter or a quality bar of §2. `:batch` variants cost half but finish within 24 hours [10], too slow for a live invitation.

---

## 2. Candidates and evidence

The Intelligence Index comes from the catalog [1]. AA-LCR and hallucination rates come from a secondary mirror of Artificial Analysis data dated 2026-09-22 [9]. The endpoint column lists the endpoints that pass filter 2, from the endpoints snapshot [1][5]. A T1 run costs 120k input plus 36k output tokens.

| Model | Weights | Intelligence Index | AA-LCR | Hallucination rate | $/M in / out | $ per T1 run | ZDR + strict JSON endpoints | Verdict |
|---|---|---|---|---|---|---|---|---|
| `anthropic/claude-opus-5.5` | closed | 57.6 | 84.7% | 58.6% | 4 / 20 | 1.20 | `google-vertex/europe`, `/global`, `/us` | **T1-A** |
| `openai/gpt-6-sol` | closed | 47.5 | 83.7% | 60.1% | 2 / 10 | 0.60 | `azure/eu`, `azure`, `azure/us` | **T1-B, T2-B** |
| `google/gemini-3.8-flash` | closed | 40.9 | 81.3% | 55.2% | 0.75 / 3.75 | 0.23 | `google-vertex/global` (plus its `/flex` and `/priority` variants) | **T1-C, T2-A** |
| `anthropic/claude-sonnet-5` | closed | 38.2 | 82.0% | 39.4% | 2 / 10 | 0.60 | `google-vertex/europe`, `/global`, `/us` | Reserve for T2-B: lower hallucination rate than GPT-6 Sol, but it shares Google Vertex AI with T2-A |
| `openai/gpt-6-astra` | closed | 52.7 | 80.7% | 51.3% | 10 / 50 | 3.00 | `azure`, `azure/us` | No: lower AA-LCR than Sol at 5× the price; no EU endpoint |
| `anthropic/claude-opus-5` | closed | 50.8 | 79.3% | 60.8% | 5 / 25 | 1.50 | as Opus 5.5 | No: Opus 5.5 scores higher and costs less |
| `x-ai/grok-4.7` | closed | 46.4 | 76.7% | 29.3% | 1.6 / 4.8 | 0.37 | `xai` (US) | Reserve for T1-C: runs on its own infrastructure, but has the lowest AA-LCR here and long reasoning (about 81k output tokens per Artificial Analysis task, secondary [9]); xAI's DPF status is UNVERIFIED |
| `xiaomi/mimo-v2.6-pro` | open | 46.3 | 86.3% | 40.6% | 0.435 / 0.87 | 0.08 | `deepinfra/fp8` only | Reserve: strong recall proxy, but one eligible endpoint, 8-bit quantized, JSON reliability unproven |
| `moonshotai/kimi-k3` | open | 43.6 | 88.7% | 51–53% [9][11] | 3 / 15 | 0.90 | third-party, mostly 4-bit | No: quantized third-party endpoints; high hallucination rate |
| `z-ai/glm-5.3` | open | 44.8 | 79.7% | 29.6% | 0.84 / 2.64 | 0.20 | many third-party | No: vetting its many providers costs more than it saves |
| `z-ai/glm-5.3-flash` | open | 41.8 | n/a | n/a | 0.15 / 0.50 | 0.04 | many third-party | No (T2): saves under $0.10 per job, with the same vetting cost |
| `qwen/qwen3.8-max-0902` | open, custom licence | 45.4 | 80.7% | n/a | 2 / 6 | 0.46 | none | Fails filter 2 |
| `deepseek/deepseek-v4.1-flash` | open | 39.5 | 84.0% | 96.5% | 0.15 / 0.60 | 0.04 | third-party | No: hallucination rate |
| `openai/gpt-6-luna` | closed | 37.3 | 83.3% | 76.7% | 0.10 / 0.50 | 0.03 | `azure/eu`, `azure`, `azure/us` | No: hallucination rate |

---

## 3. Chains

### 3.1 T1: requirements (dual extraction plus fallback)

```
                ┌─► A  anthropic/claude-opus-5.5 ──┐
 tender text ───┤                                   ├─► union ─► quote check ─► review queue
                └─► B  openai/gpt-6-sol ───────────┘

 A or B fails (after its one retry)  →  C  google/gemini-3.8-flash takes its place
 two of A, B, C fail                 →  the job stops and alerts; re-run later or extract by hand (v0)
```

- A and B run on every tender, independently. Neither sees the other's answer.
- Two items match when their verified quotes overlap on the same page. An item that only one model found is marked for the reviewer, and `found_by` is stored (`architecture.md` §8).
- C only replaces a failed A or B. It is never a third opinion.
- Exit rule: after 5 real tenders, if B never found an accepted item that A missed, B becomes a fallback only and T1 runs a single extraction.

Why these three:

- **A** has the highest Intelligence Index and the highest AA-LCR among the closed models.
- **B** has the second-highest AA-LCR among the closed models at half A's price, comes from another vendor, runs on another host (Azure) and has an EU endpoint.
- **C** is a third model vendor at a fifth of A's price, with AA-LCR 81.3%. It shares Google Vertex AI with A, so a Vertex outage removes both. Onboarding a tender is not minute-critical, so the job then waits and is re-run.

### 3.2 T2: tables (single extraction plus fallback)

A `google/gemini-3.8-flash`; B `openai/gpt-6-sol` when A fails.

- Runs only for tables the deterministic parsers cannot read. Scanned pages without a text layer never go to an LLM: the quote check needs text, so the operator types those rows.
- One extraction is enough here: tables are short, every row carries a checked quote, and the reviewer compares each row with the page.
- B runs on another vendor and another host than A, so it also covers a Google Vertex AI outage.

### 3.3 Not used, and when to add it

| Not used | Why | Add when |
|---|---|---|
| `:batch` variants (half price) | 24-hour window [10]; saves about $5 a month; whether batch works with account-wide ZDR is UNVERIFIED | Evaluation rounds grow large |
| Prompt caching | A and B are different vendors, so nothing is read twice by the same model; retries are rare | Retries or several questions over one document become common |
| PDF or image input, OpenRouter's `file-parser` plugin | The quote check needs the exact text the model saw. Plugins are outside ZDR [5], and the OCR engine sends the file to Mistral as another processor [12] | Never for T1. For scanned tables only with a sandboxed OCR step whose text also feeds the quote check |
| The `openrouter/auto` router | It picks models by community usage, not by our evaluation [3] | Never |
| Open-weight models | Served by many third parties, often quantized; each provider needs vetting | A candidate beats a chain model in §7 on an allowlisted ZDR endpoint |
| Bring-your-own vendor keys | More keys and contracts to manage; no fee saving under $25,000 a month [2] | Never at this volume |

---

## 4. Request settings

### 4.1 Every call

The T1-A request, as sent to `POST https://openrouter.ai/api/v1/chat/completions`:

```json
{
  "model": "anthropic/claude-opus-5.5",
  "messages": [
    {"role": "system", "content": "<task instructions; prompt_version>"},
    {"role": "user", "content": "<document><page n=\"1\">…</page>…</document>"}
  ],
  "response_format": {
    "type": "json_schema",
    "json_schema": {"name": "tender_requirements", "strict": true, "schema": {}}
  },
  "reasoning": {"effort": "high", "exclude": true},
  "max_tokens": 96000,
  "stream": true,
  "provider": {
    "order": ["google-vertex/europe", "google-vertex"],
    "allow_fallbacks": false,
    "require_parameters": true,
    "data_collection": "deny",
    "zdr": true,
    "max_price": {"prompt": 5, "completion": 25}
  }
}
```

- `schema` holds the extraction schema; each item carries `page` and a verbatim `quote`. Some providers treat a schema as a strong hint rather than a guarantee [13], so our own validation after parsing is the control. `require_parameters: true` also keeps requests away from endpoints that would ignore `response_format` [13].
- The system message holds the instructions and says that the document is data, never instructions. The user message holds only the document, one `<page>` element per page, exactly as the sandboxed parser produced it (`architecture.md` §6.9, LLM01).
- `provider`: `order` tries the listed endpoints in that order, and `allow_fallbacks: false` stops there instead of trying other providers [4]. Region slugs such as `google-vertex/europe` are documented [4]; a plain slug such as `google-vertex` matches any of that provider's endpoints. `data_collection: "deny"` excludes providers that keep data or may train on it [4]. `max_price` makes the request fail rather than run above the cap [4].
- `stream: true`: a high-effort call on 120k tokens can take minutes, and a streamed response does not leave the connection idle that long. The job reads the stream to the end and parses only the complete answer.
- Never sent: `temperature`, `top_p`, `top_k`, `seed` (§5), `tools`, `plugins`, `models`.

### 4.2 Per step

| Step | `model` | `provider.order` | `reasoning.effort` | `max_tokens` | `max_price` $/M (prompt / completion) |
|---|---|---|---|---|---|
| T1-A | `anthropic/claude-opus-5.5` | `google-vertex/europe`, `google-vertex` | `high` | 96000 | 5 / 25 |
| T1-B | `openai/gpt-6-sol` | `azure/eu`, `azure` | `high` | 96000 | 3 / 15 |
| T1-C | `google/gemini-3.8-flash` | `google-vertex/global` | `high` | 65536 (the model's maximum) | 1 / 5 |
| T2-A | `google/gemini-3.8-flash` | `google-vertex/global` | `low` | 16000 | 1 / 5 |
| T2-B | `openai/gpt-6-sol` | `azure/eu`, `azure` | `low` | 16000 | 3 / 15 |

The price caps sit 25–50% above today's prices: a price rise makes requests fail loudly, and the owner reviews it.

### 4.3 Reasoning

Applied from OpenRouter's reasoning-token guide [6]:

- **Effort per task**: `high` for T1, where recall matters most, and `low` for T2. For Claude, OpenRouter turns `effort` into a thinking budget; for GPT-6 it passes the effort through; for Gemini 3 it maps effort to a thinking level.
- **Room for the answer.** Reasoning tokens count against `max_tokens`. For Claude, the guide gives a budget of about 80% of `max_tokens` at `high`; at 96,000 that leaves about 19,000 tokens for the answer, above the expected 12k. Whether this formula still applies to Opus 5.5, which thinks adaptively, is UNVERIFIED (§8), so the evaluation records reasoning tokens and finish reasons. If a run ends with `length`, raise `max_tokens` first (Claude and GPT-6 allow 128,000 [1]); lower the effort only after that.
- **`exclude: true`**: the reasoning is billed but not returned. We never store or show it, and reasoning can repeat instructions planted in a document, so not receiving it removes one more place where injected text could surface.
- **A failed budget is a failed run**: `finish_reason: "length"` with empty or partial content is billed like a full run and is never used (§4.4).
- Passing reasoning back between turns does not apply: every call is a single turn without tools.

### 4.4 Handling each result

| Outcome of an attempt | Action |
|---|---|
| Network error, timeout, HTTP 408, 429 or 5xx | Retry the same step once, after the `Retry-After` delay when given [8], else after a backoff with jitter; then the next model |
| HTTP 400 | Alert, then the next model: a schema feature that one model rejects may work on another. If every model fails, the request itself is wrong |
| HTTP 401, 402 or 403 | Stop the job and alert. A key problem, an exhausted credit or spend limit, or a guardrail block fails on every model [8][27] |
| HTTP 404, no endpoint found | Routing changed, for example a provider dropped a model or a parameter: alert, then the next model |
| `finish_reason: "length"`, or empty content | Failed run, still billed [6]. Retry once with `max_tokens` at the model's maximum, then the next model |
| Any other `finish_reason` than `stop` | Failed run: the next model |
| Content that does not parse as JSON or fails our schema | Failed run: the next model. The JSON is never repaired |
| An item whose quote is not found on its page | The item is rejected and shown to the reviewer as rejected (`architecture.md` §6.9 step 4); the run stays valid |
| Two of A, B, C failed (T1), or both steps failed (T2) | The job stops and alerts. The operator re-runs it later or extracts by hand (v0 process) |

### 4.5 What each attempt records

One `extraction_run` row per attempt (`architecture.md` §8): task and step; the requested model; the model and provider that answered; the generation `id`; prompt and schema versions; `finish_reason`; token counts including reasoning tokens; cost; latency; outcome. The raw answer is kept (public data). Answers are not repeatable (§5.2), so the stored answer, not a re-run, is the record behind every reviewed row. `GET /api/v1/generation?id=…` returns the upstream provider, cost and data region for an audit [14].

---

## 5. Sampling parameters (temperature)

### 5.1 Per call

"Endpoints accept" reads the `supported_parameters` of the endpoints that each step may use, from the endpoints snapshot [1].

| Call | Model | Vendor rule while reasoning | Endpoints accept `temperature`? | Sent | Runs at |
|---|---|---|---|---|---|
| T1-A | `claude-opus-5.5` | Models released after Claude Opus 4.6 do not support setting `temperature`: 1.0 is accepted for backwards compatibility, any other value is rejected [30]. Opus 4.7, 4.8 and Opus 5 also reject `top_p` and `top_k` [16] | No | Nothing | 1.0 |
| T1-B, T2-B | `gpt-6-sol` | Not accepted while reasoning: OpenAI says to remove `temperature` and `top_p` from every GPT-6 model unless reasoning effort is `none` [17]. We need reasoning. No GPT-6 endpoint on OpenRouter accepts them at all [1] | No | Nothing | 1, OpenAI's default |
| T1-C, T2-A | `gemini-3.8-flash` | Accepted, but Google strongly recommends the default 1.0 for Gemini 3 models; lower values may cause looping or weaker reasoning [18]. Not restated for 3.8 (UNVERIFIED for 3.8) | No on Vertex AI; only AI Studio accepts it, and AI Studio is not ZDR | Nothing | 1.0, the default |
| Reserve | `claude-sonnet-5` | As Opus 5.5: only 1.0 is accepted [15][30] | No | Nothing | 1.0 |
| Reserve | `grok-4.7` | xAI documents no rule for reasoning models (UNVERIFIED) [19]. OpenRouter lists defaults of 0.7 and `top_p` 0.95 [1] | Yes | Nothing; evaluate at the default if it enters a chain | Provider default (UNVERIFIED) |
| Reserve | `mimo-v2.6-pro` | In thinking mode the model forces 1.0 and `top_p` 0.95 [20] | Yes | Nothing | 1.0, forced |

OpenRouter's own rules: `temperature` ranges from 0 to 2 with a default of 1.0 [25]. Without `require_parameters`, a provider that does not support a parameter ignores it; with `require_parameters: true`, such a provider is not used at all [4]. A `temperature` on any chain step would therefore leave no eligible endpoint, and the request would fail ("no endpoints found", secondary report [26]). Whether OpenRouter fills in a model's `default_parameters` when a request omits them is UNVERIFIED; the three chain models list none.

### 5.2 Evidence

- **Temperature 0 does not make answers repeatable.** In production inference the result depends on how the server batches concurrent requests, even with greedy decoding [21]. OpenAI describes its `seed` as best effort [22]. Anthropic's migration notes say that temperature 0 never guaranteed identical outputs [16].
- **Temperature and accuracy.** Across nine models and several prompting methods on problem-solving benchmarks, temperatures from 0.0 to 1.0 made no statistically significant difference [23]. A 2026 study of one extended-reasoning model (Grok-4.1) on 39 maths problems found zero-shot accuracy best at moderate temperatures, and a larger gain from extended reasoning at higher temperatures [24]. That is one model and few problems, on maths rather than extraction.
- No study was found on temperature for long-document extraction with reasoning models and strict JSON output.

### 5.3 Decision

- **Every step of T1 and T2 sends no sampling parameter, so every call runs at temperature 1**: Claude accepts only 1.0, GPT-6 runs at its default of 1 while reasoning, and Gemini's default is 1.0. This is the only setting that all three chain models accept, that their vendors recommend, and that keeps the ZDR endpoints eligible.
- Variance is controlled by strict JSON, verified quotes, dual extraction (T1) and human review. It is measured by three runs per model per gold tender (§7).
- Revisit when a model enters a chain and its vendor recommends a non-default value, or when the evaluation shows run-to-run variance on a model that accepts a sampling setting.

---

## 6. Privacy and account settings

**Data path.** Our server (EU) → OpenRouter (a US company) → Google Vertex AI (Claude, Gemini) or Microsoft Azure (GPT-6 Sol), EU endpoint first → back. The content is public tender text only; dependency rule 5 of `architecture.md` keeps client data out of this path. For commercial use, OpenRouter's terms incorporate a data-processing agreement, and Enterprise customers get a countersigned copy; this comes from a secondary relay, so the wording is UNVERIFIED [29]. Routing that keeps all processing in the EU (`eu.openrouter.ai`) is Enterprise-only [28]. It is not needed while only public text is sent, and client data must never be sent (`architecture.md` AD10).

**Account and key settings**, set once and checked at the v3 gate:

| Setting | Value | Why |
|---|---|---|
| ZDR on the account | Enforced for all five scopes: Anthropic, OpenAI, Google, xAI, other [5] | A second layer behind `zdr: true` in every request |
| Providers that may train on inputs | Blocked, for paid and free models [28] | Defence in depth |
| Guardrail: models | Allowlist of the three chain models [27] | A code bug or a stolen key cannot reach other models |
| Guardrail: providers | Allowlist `google-vertex`, `azure` [27] | The same, for providers |
| Guardrail: spend | Daily limit on the production key, for example $20, set by the owner; a breach returns HTTP 402 [27] | OWASP LLM10, unbounded consumption |
| Key credit limit | For example $100 on production and $10 on dev, set by the owner [8] | Caps the loss from a leaked key |
| Guardrail: sensitive-information redaction | Off | Redaction changes the text the model sees, so the quote check would fail against the original |
| Guardrail: prompt-injection patterns | Off | Tender text could match generic patterns, and a match returns HTTP 403 and stops the job [27]. Injection is handled by the controls of `architecture.md` §6.9 |
| Plugins (web search, file parser) | Never requested | ZDR does not cover plugins [5] |
| Keys | One per environment, in the platform secret store, used only by `adapters/llm_openrouter`, rotated | Least privilege (`architecture.md` C3) |

---

## 7. Evaluation gate

**Gold set.** T1: the current tender's hand-built [`requirements.csv`](../tenders/pkm-meth-student-transport-dsa-2026/requirements.csv) (R1–R26) with the text of its διακήρυξη [7], plus a second tender before v3 goes live: one tender cannot show recall on others. T2: a hand-checked route table from the first real invitation that needs T2.

**Protocol.**

- The production code path and settings: the same request builder, prompt and schema versions, provider settings and `max_tokens`. An evaluation with other settings measures another system.
- Every chain model alone: T1-A, T1-B and T1-C (C must pass alone, because it replaces A or B); T2-A and T2-B.
- Three runs per model per gold tender, to measure run-to-run variance (§5).

**Measured per run.** Recall (gold requirements found, graded by a person against `§` and meaning); precision (extracted items that are real requirements); quote pass rate; schema validity with reasoning on (the guide does not say that reasoning and strict structured output work together [6]); `finish_reason`; reasoning and answer tokens; cost; latency; the provider that answered, which also checks that `order` picked the EU endpoint.

**Pass bar for a chain model.** Recall of 100% on every gold tender in 3 of 3 runs; valid schema in 3 of 3; no `length`. The owner sets the precision threshold before v3. A model that misses gold items at `high` is tried once at `xhigh` before it is rejected.

**Re-run** when a chain model changes, or its endpoint snapshot (for example `anthropic/claude-opus-5.5-20260921` in the endpoints snapshot [1]), a provider in `order`, the prompt or the schema.

---

## 8. Refresh and open items

**Refresh** at least quarterly, and whenever a chain model gets an `expiration_date` or a new endpoint snapshot:

1. Write new dated snapshots of the catalog and the candidates' endpoints in [`reference/`](../reference/CONTEXT.md), following the procedure in its `CONTEXT.md`.
2. Re-apply §1.2, re-rank §2 and check that every chain step still has a ZDR endpoint with strict JSON, EU first where one exists.
3. Run §7 for every change to a chain.

| Item | Status | How to close it |
|---|---|---|
| Greek extraction quality of every candidate | UNVERIFIED: no benchmark | §7 |
| Reasoning together with strict structured outputs | Not documented [6] | §7 records schema validity with reasoning on |
| How OpenRouter maps `effort` for Claude Opus 5.5, which thinks adaptively | UNVERIFIED | §7 records reasoning tokens and finish reasons |
| Gemini 3.8 follows the Gemini 3 temperature guidance | Stated for Gemini 3, not restated for 3.8 | No impact while no sampling parameter is sent |
| Region slugs (`google-vertex/europe`, `azure/eu`) route as intended | Region slugs are documented [4]; ours are untested | §7 records the provider of each run |
| OpenRouter's DPA wording, its own log retention and its DPF certification | UNVERIFIED | Read its terms, DPA and privacy policy before v3 |
| Whether `default_parameters` are applied when a request omits them | UNVERIFIED | No impact on the chain models, which list none |
| AA-LCR and hallucination rates | Secondary mirror [9] | Re-check on artificialanalysis.ai at each refresh |

---

## 9. Sources

Research done on 2026-09-23.

1. OpenRouter catalog snapshot: [`reference/openrouter-models-2026-09-23.csv`](../reference/openrouter-models-2026-09-23.csv), from `GET https://openrouter.ai/api/v1/models`; endpoints snapshot of the 14 candidates: [`reference/openrouter-endpoints-2026-09-23.csv`](../reference/openrouter-endpoints-2026-09-23.csv), from `GET https://openrouter.ai/api/v1/models/{author}/{slug}/endpoints` and the ZDR list [5].
2. OpenRouter FAQ (5.5% fee on card credit purchases; no markup on model prices; bring-your-own-key fees): https://openrouter.ai/docs/faq
3. OpenRouter model fallbacks: https://openrouter.ai/docs/guides/routing/model-fallbacks · auto router: https://openrouter.ai/docs/features/model-routing
4. OpenRouter provider routing (`order`, `only`, `allow_fallbacks`, `require_parameters`, `data_collection`, `zdr`, `max_price`, region slugs): https://openrouter.ai/docs/features/provider-routing
5. OpenRouter zero data retention: https://openrouter.ai/docs/guides/features/zdr · ZDR endpoint list (900 endpoints on 2026-09-23): https://openrouter.ai/api/v1/endpoints/zdr
6. OpenRouter reasoning tokens: https://openrouter.ai/docs/guides/best-practices/reasoning-tokens
7. Διακήρυξη ΔΣΑ Μεταφοράς Μαθητών Μ.Ε. Θεσσαλονίκης, ΑΔΑ ΨΡΘ97ΛΛ-ΕΕΚ (2026-03-06): https://diavgeia.gov.gr/doc/ΨΡΘ97ΛΛ-ΕΕΚ
8. OpenRouter API limits (free-model caps, key credit limits, 402 and 429 handling): https://openrouter.ai/docs/api-reference/limits
9. Artificial Analysis model pages, e.g. https://artificialanalysis.ai/models/claude-opus-5-5 , https://artificialanalysis.ai/models/gpt-6-sol , https://artificialanalysis.ai/models/gemini-3-8-flash , https://artificialanalysis.ai/models/grok-4-7 · AA-LCR and AA-Omniscience hallucination rates through a secondary mirror, snapshot 2026-09-22: https://benchlm.ai/benchmarks/lcr
10. OpenRouter Batch API (half price, 24-hour window, results kept 30 days): https://openrouter.ai/docs/batch-quickstart
11. Kimi K3 hallucination rate (secondary): https://kili-technology.com/blog/kimi-k3s-benchmarks-and-hallucinations----what-that-tells-us-about-ai-evaluation
12. OpenRouter PDF input and the `file-parser` plugin: https://openrouter.ai/docs/guides/overview/multimodal/pdfs
13. OpenRouter structured outputs: https://openrouter.ai/docs/features/structured-outputs
14. OpenRouter generation record: https://openrouter.ai/docs/api-reference/get-a-generation
15. Anthropic, What's new in Claude Sonnet 5 (sampling parameters): https://platform.claude.com/docs/en/models/sonnet-5/whats-new-sonnet-5
16. Claude API reference bundled with Claude Code 2.1.280, `shared/model-migration.md` and `shared/error-codes.md`: sampling parameters rejected on Opus 4.7, 4.8 and Opus 5; temperature 0 never guaranteed identical outputs.
17. OpenAI, latest-model guide: https://developers.openai.com/api/docs/guides/latest-model · GPT-6 Sol: https://developers.openai.com/api/docs/models/gpt-6-sol
18. Google, Gemini 3 developer guide (temperature): https://ai.google.dev/gemini-api/docs/gemini-3
19. xAI chat completions reference: https://docs.x.ai/developers/rest-api-reference/inference/chat-completions · reasoning: https://docs.x.ai/developers/model-capabilities/text/reasoning
20. Xiaomi MiMo-V2.6-Pro model card: https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL/blob/main/README.md
21. Thinking Machines Lab, *Defeating Nondeterminism in LLM Inference* (September 2025): https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
22. OpenAI Cookbook, reproducible outputs with the `seed` parameter: https://cookbook.openai.com/examples/reproducible_outputs_with_the_seed_parameter
23. M. Renze, E. Guven, *The Effect of Sampling Temperature on Problem Solving in Large Language Models*, arXiv:2402.05201 (2024): https://arxiv.org/abs/2402.05201
24. M. Salah, A. Muneer, *Temperature-Dependent Performance of Prompting Strategies in Extended Reasoning Large Language Models*, arXiv:2604.08563 (2026-03-18): https://arxiv.org/abs/2604.08563
25. OpenRouter request parameters: https://openrouter.ai/docs/api-reference/parameters
26. "No endpoints found" when `require_parameters` excludes every provider (secondary): https://github.com/anomalyco/opencode/issues/10594
27. OpenRouter guardrails (model and provider allowlists, spend limits, prompt-injection and sensitive-information filters): https://openrouter.ai/docs/guides/features/guardrails
28. OpenRouter privacy and logging (training settings; EU in-region routing for Enterprise): https://openrouter.ai/docs/features/privacy-and-logging
29. OpenRouter DPA, Help Center (direct fetch refused with HTTP 403; content through a search relay, secondary): https://openrouter.zendesk.com/hc/en-us/articles/47828437697051
30. Anthropic Messages API reference (`temperature` deprecated; models released after Claude Opus 4.6 accept only 1.0): https://platform.claude.com/docs/en/api/messages
