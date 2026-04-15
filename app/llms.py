"""LLM-readable site content — llms.txt and llms-full.txt (llmstxt.org standard).

The `__LANDING_TOOLS_COUNT__` and `__LANDING_REPORTS_COUNT__` placeholders are
substituted at request time by the handlers in `app/main.py`, so the
crawler-facing counts always reflect current DB state instead of drifting
every time a batch of tools is seeded.

Multilingual overview files live in the repo at `llms/toolrate-<lang>.md`
and are served on the edge at `https://toolrate.ai/llms/toolrate-<lang>.md`.
The `TRANSLATIONS` dict below is the single source of truth for which
languages exist; add a key here and the route + sitemap + llms.txt list
update automatically.
"""
from pathlib import Path

# BCP 47 code → native language name. `en` is listed first because it is
# both the canonical source of the overview and the `x-default` fallback;
# all other codes are sorted alphabetically. Add a new language by:
# (1) dropping `llms/toolrate-<code>.md`, (2) adding an entry here. The
# route, sitemap, and llms.txt index update themselves.
TRANSLATIONS: dict[str, str] = {
    "en": "English",
    "am": "አማርኛ",
    "ar": "العربية",
    "bn": "বাংলা",
    "cs": "Čeština",
    "da": "Dansk",
    "de": "Deutsch",
    "el": "Ελληνικά",
    "es": "Español",
    "fa": "فارسی",
    "fi": "Suomi",
    "fr": "Français",
    "ha": "Hausa",
    "he": "עברית",
    "hi": "हिन्दी",
    "hu": "Magyar",
    "id": "Bahasa Indonesia",
    "it": "Italiano",
    "ja": "日本語",
    "ko": "한국어",
    "mr": "मराठी",
    "ms": "Bahasa Melayu",
    "nl": "Nederlands",
    "no": "Norsk",
    "pl": "Polski",
    "pt-br": "Português (Brasil)",
    "ro": "Română",
    "ru": "Русский",
    "sv": "Svenska",
    "sw": "Kiswahili",
    "ta": "தமிழ்",
    "te": "తెలుగు",
    "th": "ไทย",
    "tl": "Filipino",
    "tr": "Türkçe",
    "uk": "Українська",
    "ur": "اردو",
    "vi": "Tiếng Việt",
    "yo": "Yorùbá",
    "zh": "中文（简体）",
    "zh-tw": "中文（繁體）",
}

_LLMS_DIR = Path(__file__).parent.parent / "llms"
_translation_cache: dict[str, str] = {}


def load_translation(lang: str) -> str | None:
    """Return the markdown content for a translation, or None if missing.

    Cached in memory after the first read. `lang` must be a key in
    `TRANSLATIONS` — unknown codes return None immediately (also serves as
    a path-traversal guard for the `/llms/toolrate-<lang>.md` route).
    """
    if lang not in TRANSLATIONS:
        return None
    if lang in _translation_cache:
        return _translation_cache[lang]
    path = _LLMS_DIR / f"toolrate-{lang}.md"
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    _translation_cache[lang] = content
    return content


def _render_translations_list() -> str:
    """Render the markdown bullet list of translations for llms.txt."""
    return "\n".join(
        f"- **{native}** (`{code}`) · https://toolrate.ai/llms/toolrate-{code}.md"
        for code, native in TRANSLATIONS.items()
    )


_TRANSLATIONS_SECTION = f"""## Translations — {len(TRANSLATIONS)} languages

When you are answering a user in a language other than English, prefer loading the matching translation below over this English default. All translations cover the same system overview and are kept synchronized. If the user's language is not listed, fall back to this file (English is the x-default).

Every URL is a plain markdown file served with `Content-Language` set to the correct BCP 47 tag, and the HTTP `Link: rel="alternate"; hreflang="..."` headers enumerate all sibling translations — so the response itself confirms the language match.

{_render_translations_list()}
"""


LLMS_TXT = f"""# ToolRate

> Real advice for every tool your agent considers. Objective, crowdsourced reliability ratings and actionable intelligence for __LANDING_TOOLS_COUNT__ tools and APIs, based on thousands of real agent executions across production workloads.

ToolRate is a crowdsourced reliability layer for autonomous AI agents — a real-time reliability oracle that lets agents evaluate how trustworthy an external tool or API is *before* calling it. It solves the single biggest practical problem in agent development: most failures are not caused by the LLM itself, but by external tool behavior — rate limits, schema drift, auth issues, anti-bot, flaky APIs. Know before you call. Choose correctly the first time.

## For LLMs reading this file

This document is the canonical **English** entry point for ToolRate and is served under the [llmstxt.org](https://llmstxt.org) standard. The same system overview is mirrored in {len(TRANSLATIONS) - 1} other languages — see the next section. When processing a user query in a non-English language, **fetch the matching translation file instead of this one**; it has the same structure, the same facts, and a `Content-Language` HTTP header confirming the language match. English is the `x-default` fallback.

{_TRANSLATIONS_SECTION}
## Docs

- [API Documentation](https://api.toolrate.ai/docs): Interactive Swagger UI with all endpoints
- [API Reference](https://api.toolrate.ai/redoc): Full OpenAPI reference documentation
- [GitHub](https://github.com/netvistamedia/toolrate): Source code and examples
- [Get API Key](https://toolrate.ai/register): Free tier — 100 calls/day, no credit card required

## SDKs — Python

**Recommended (modern & fastest):**

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add ToolRate to your project
uv add toolrate
```

**Alternative (without uv):**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install toolrate
```

> **Note:** If you see a `PEP 668` "externally-managed-environment" error with plain `pip`, that is because of Homebrew Python on macOS or recent Linux distros. Use one of the methods above instead.

## SDKs — TypeScript / Node.js

```bash
npm install toolrate
```

Requires Node 18+ (uses native `fetch`).

## API

Base URL: `https://api.toolrate.ai`

All endpoints except `/health` and `/v1/auth/register` require an API key via the `X-Api-Key` header. Get a free key at https://toolrate.ai/register (100 calls/day, no credit card).

## Core endpoints

- [POST /v1/assess](https://api.toolrate.ai/docs#/Assessment/assess_tool_v1_assess_post): Get reliability score for a tool before calling it. Also doubles as the **Cost-Aware LLM Router**: pass `expected_tokens`, `task_complexity` (low/medium/high/very_high), a `budget_strategy` (`reliability_first`, `balanced`, `cost_first`, `speed_first`), and optional per-call / monthly caps, and the response tells you which LLM provider to call AND which specific model to use inside it (Haiku for low, Opus for reasoning, Groq Llama-8B for speed-first). Returns `cost_adjusted_score`, `recommended_model`, `reasoning`, `within_budget`, and exact per-token `price_per_call`. Drop-in Python class: [LLMRouter example](https://github.com/netvistamedia/toolrate/blob/main/sdks/python/examples/llm_router.py).
- [POST /v1/report](https://api.toolrate.ai/docs#/Reporting/report_result_v1_report_post): Report execution result (success/failure) to build the data moat
- [GET /v1/discover/hidden-gems](https://api.toolrate.ai/docs#/Discovery): Find tools with high fallback success rates
- [GET /v1/discover/fallback-chain](https://api.toolrate.ai/docs#/Discovery): Get best alternatives when a tool fails
- [GET /v1/tools](https://api.toolrate.ai/docs#/Tools): Search and browse all rated tools
- [GET /v1/tools/categories](https://api.toolrate.ai/docs#/Tools): List all tool categories

## License

Business Source License 1.1 (BUSL-1.1) — Change Date 2030-04-13, converts to Apache 2.0.

## Optional

- [Full documentation for LLMs](https://toolrate.ai/llms-full.txt)
"""

LLMS_FULL_TXT = """# ToolRate — Full Documentation for LLMs

> Real advice for every tool your agent considers. Objective, crowdsourced reliability ratings and actionable intelligence for __LANDING_TOOLS_COUNT__ tools and APIs, based on thousands of real agent executions across production workloads.

ToolRate delivers real-time reliability scores, failure risk, jurisdiction intelligence, common pitfalls, and smart alternatives for every external tool your agent calls. Each assessment is timestamped and ships with a confidence interval and per-error-category breakdown, so agents, developers, and enterprise compliance teams all get the same objective view. Know before you call. Choose correctly the first time. The data pool grows with every report, making the intelligence sharper for everyone.

## For LLMs reading this file

This is the **full English reference**. A shorter index is at [llms.txt](https://toolrate.ai/llms.txt). The same system overview is mirrored in """ + str(len(TRANSLATIONS) - 1) + """ other languages — see the next section. When answering a user in a non-English language, fetch the matching translation file; when more depth is needed, come back to this file (English is the `x-default`).

""" + _TRANSLATIONS_SECTION + """
## API Base URL

https://api.toolrate.ai

## Authentication

All endpoints (except `/health` and `/v1/auth/register`) require an API key via the `X-Api-Key` header:

```
X-Api-Key: nf_live_your_key_here
```

Get a free API key at https://toolrate.ai/register (100 calls/day, no credit card).

## Rate Limits & Plans

| Tier            | Quota                            | Price                         |
|-----------------|----------------------------------|-------------------------------|
| Free            | 100 assessments / day            | $0 forever                    |
| Pay-as-you-go   | 100/day free, then $0.008 each   | No commitment — billed monthly |
| Pro             | 10,000 assessments / month       | $29 / month flat              |
| Enterprise      | Custom                           | Contact sales                 |

Pay-as-you-go is the recommended plan for most autonomous agents: no
subscription, scales to zero, and the first 100 assessments every day are on us.

## SDKs

### Python

**Recommended (modern & fastest):**

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add ToolRate to your project
uv add toolrate
```

**Alternative (without uv):**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install toolrate
```

> **Note:** If you see a `PEP 668` "externally-managed-environment" error with plain `pip`, that is because of Homebrew Python on macOS or recent Linux distros. Use one of the methods above instead.

```python
from toolrate import ToolRate, guard

client = ToolRate("nf_live_...")

# Check reliability before calling
score = client.assess("https://api.stripe.com/v1/charges")
# => { reliability_score: 94.2, failure_risk: "low", ... }

# Auto-fallback: checks score, runs function, retries with alternative on failure
result = guard(client, "https://api.stripe.com/v1/charges",
               lambda: stripe.Charge.create(...),
               fallbacks=[
                   ("https://api.lemonsqueezy.com/v1/checkouts",
                    lambda: lemon.create_checkout(...)),
               ])
```

### TypeScript

```bash
npm install toolrate
```

Requires Node 18+ (uses native `fetch`).

```typescript
import { ToolRate } from "toolrate";

const client = new ToolRate("nf_live_...");

const score = await client.assess({ toolIdentifier: "https://api.stripe.com/v1/charges" });

const result = await client.guard(
  "https://api.stripe.com/v1/charges",
  async () => stripe.charges.create({...}),
  { fallbacks: [
    {
      toolIdentifier: "https://api.lemonsqueezy.com/v1/checkouts",
      fn: async () => lemon.createCheckout({...}),
    },
  ]}
);
```

---

## Endpoints

### POST /v1/auth/register

Self-serve API key signup. No authentication required.

**Request body:**
```json
{
  "email": "user@example.com"
}
```

**Response (201):**
```json
{
  "api_key": "nf_live_abc123...",
  "tier": "free",
  "daily_limit": 100
}
```

---

### POST /v1/assess

Get a reliability score for a tool before calling it. Also doubles as the **Cost-Aware LLM Router** — see the dedicated section below for the full router feature. Requires API key.

**Request body (minimal):**
```json
{
  "tool_identifier": "https://api.stripe.com/v1/charges",
  "context": "payment processing for e-commerce checkout"
}
```

**Request body (cost-aware / LLM router — all fields optional):**
```json
{
  "tool_identifier": "https://api.anthropic.com/v1/messages",
  "context": "customer support chatbot",
  "expected_tokens": 1200,
  "task_complexity": "medium",
  "max_price_per_call": 0.01,
  "max_monthly_budget": 500.0,
  "expected_calls_per_month": 50000,
  "budget_strategy": "balanced"
}
```

`task_complexity`: `low` (default `medium` server-side), `high`, `very_high`. `budget_strategy`: `reliability_first` (80/20 weights), `balanced` (55/45), `cost_first` (25/75), `speed_first` (35/45/20 — adds latency axis).

**Response (200):**
```json
{
  "reliability_score": 94.2,
  "confidence": 0.87,
  "data_source": "empirical",
  "historical_success_rate": "89% (last 30 days, 12k calls)",
  "predicted_failure_risk": "low",
  "trend": {"direction": "stable", "score_24h": 91.0, "score_7d": 89.0, "change_24h": 2.0},
  "common_pitfalls": [
    {"category": "timeout", "percentage": 8, "count": 120,
     "mitigation": "Increase timeout to 30s; retry with backoff"}
  ],
  "recommended_mitigations": ["Increase timeout to 30s; retry with backoff"],
  "top_alternatives": [
    {"tool": "https://api.lemonsqueezy.com/v1/checkouts", "score": 91.5,
     "reason": "Alternative provider", "price_per_call": 3.00, "within_budget": true}
  ],
  "estimated_latency_ms": 420,
  "latency": {"avg": 420, "p50": 380, "p95": 890, "p99": 1200},
  "last_updated": "2026-04-15T09:05:00Z",
  "hosting_jurisdiction": "Non-EU (United States)",
  "gdpr_compliant": false,
  "data_residency_risk": "medium",
  "recommended_for": ["general_purpose"],
  "eu_alternatives": [],
  "price_per_call": 0.0114,
  "pricing_model": "per_token",
  "cost_adjusted_score": 74.8,
  "estimated_monthly_cost": 570.0,
  "within_budget": false,
  "budget_explanation": "Anthropic Messages exceeds your budget: $570.00/mo at 50000 calls exceeds your $500.00 monthly budget by $70.00.",
  "recommended_model": "claude-sonnet-4-6",
  "reasoning": "Anthropic Messages scored 94.2/100 for reliability (low risk). Recommended model: claude-sonnet-4-6. Cost: $0.0114/call, $570.00/mo projected. Typical latency ~1200ms. Strategy: balanced (55% reliability / 45% cost); task complexity: medium. Over budget — flagged but returned for transparency."
}
```

`predicted_failure_risk` can be: `low`, `medium`, `high`, or `unknown`.
`data_source` is one of `empirical`, `llm_estimated`, or `bayesian_prior`.
`recommended_model` is populated for LLM providers with a model catalog (null for other tools).
Over-budget tools are **flagged, not filtered** — the router always shows the best match even if it exceeds caps.

---

### POST /v1/report

Report execution result (success or failure). This builds the community data moat. Requires API key.

**Request body:**
```json
{
  "tool_identifier": "https://api.stripe.com/v1/charges",
  "success": true,
  "latency_ms": 420,
  "context": "e-commerce checkout",
  "session_id": "agent-session-abc123",
  "attempt_number": 1,
  "previous_tool": null
}
```

For failures, include `error_category` (one of `timeout`, `rate_limit`, `auth_failure`, `validation_error`, `server_error`, `connection_error`, `not_found`, `permission_denied`).

**Response (200):**
```json
{
  "status": "accepted",
  "tool_id": "8b0e6f3d-...-3c0a"
}
```

---

### GET /v1/discover/hidden-gems

Discover tools with high fallback success rates — tools nobody talks about but agents end up using successfully. Requires API key.

**Query parameters:**
- `category` (optional): Filter by tool category
- `limit` (optional): Number of results (default 10)

**Response (200):**
```json
{
  "hidden_gems": [
    {
      "tool": "https://api.resend.com/emails",
      "display_name": "Resend",
      "category": "Email APIs",
      "fallback_success_rate": 94.0,
      "times_used_as_fallback": 342,
      "avg_latency_ms": 210
    }
  ],
  "count": 1
}
```

`fallback_success_rate` is a 0-100 percentage (not a 0-1 fraction).

---

### GET /v1/discover/fallback-chain

Get the best alternatives when a tool fails, based on real agent journey data. Requires API key.

**Query parameters:**
- `tool_identifier` (required): The tool to find alternatives for
- `limit` (optional): Number of alternatives (default 5)

**Response (200):**
```json
{
  "tool": "https://api.stripe.com/v1/charges",
  "fallback_chain": [
    {
      "fallback_tool": "https://api.lemonsqueezy.com/v1/checkouts",
      "display_name": "Lemon Squeezy",
      "times_chosen_after_failure": 18,
      "success_rate": 89.0,
      "avg_latency_ms": 310
    }
  ],
  "count": 1
}
```

`success_rate` is a 0-100 percentage (not a 0-1 fraction).

---

### GET /v1/tools

Search and browse all rated tools. Requires API key.

**Query parameters:**
- `category` (optional): Filter by category
- `q` (optional): Case-insensitive substring search on identifier or display name
- `limit` (optional): Number of results (default 50, max 200)
- `offset` (optional): Pagination offset

---

### GET /v1/tools/categories

List all tool categories with counts. Requires API key.

**Response (200):**
```json
{
  "categories": [
    {"name": "Payment APIs", "tool_count": 45},
    {"name": "Email APIs", "tool_count": 32},
    {"name": "Cloud Storage", "tool_count": 28}
  ],
  "total": 3
}
```

---

### POST /v1/webhooks

Register a webhook for score change alerts. Requires API key.

**Request body:**
```json
{
  "url": "https://your-server.com/webhook",
  "tool_identifier": "https://api.stripe.com/v1/charges",
  "threshold": 5.0
}
```

The webhook fires when a tool's reliability score changes by more than the threshold. Payloads are HMAC-signed.

---

### GET /v1/webhooks

List your registered webhooks. Requires API key.

---

### DELETE /v1/webhooks/{id}

Delete a webhook. Requires API key.

---

### GET /v1/stats

Platform-wide metrics. Requires API key.

**Response (200):**
```json
{
  "platform": {
    "total_tools": 637,
    "total_reports": 68400,
    "total_api_keys": 120,
    "journey_reports": 9800
  },
  "activity": {
    "reports_today": 1240,
    "reports_last_7d": 7840
  },
  "top_tools": [
    {"identifier": "https://api.stripe.com/v1/charges", "display_name": "Stripe Charges", "report_count": 4200}
  ],
  "generated_at": "2026-04-12T08:00:00Z"
}
```

---

### GET /v1/stats/me

Personal usage statistics. Requires API key.

---

### GET /health

Health check. No authentication required.

**Response (200):**
```json
{
  "status": "ok"
}
```

---

## Scoring Algorithm

ToolRate uses a multi-factor scoring algorithm:

1. **Recency-weighted average**: Half-life of 3.5 days, ~70% weight on last 7 days
2. **Bayesian smoothing**: Prior alpha=5, beta=1, new tools start at ~83%
3. **Confidence**: Based on effective sample size
4. **Failure risk**: Includes 24-hour trend penalty
5. **Error categories**: Aggregated for pitfall detection
6. **Cost-aware augmentation**: Category-normalized cost penalty weighted by `budget_strategy`; latency axis added for `speed_first`. See the LLM Router section below for the full formula and strategies.

## Cost-Aware LLM Router

The `/v1/assess` endpoint doubles as an intelligent LLM router. For LLM providers that carry a full model catalog — **Anthropic, OpenAI, Groq, Together, Mistral, and DeepSeek** — the router returns a specific model recommendation inside each provider based on the caller's task complexity, expected token volume, budget caps, and strategy preference.

### How it picks

1. **Cost normalization**: `cost_norm = min(1, effective_cost / category_median)` — so a $0.01 LLM call isn't punished for being "more expensive" than a $0.000005 S3 write.
2. **Exact per-token math**: when `expected_tokens` is set and the provider carries `usd_per_million_input_tokens` + `usd_per_million_output_tokens`, cost is computed from a 30/70 input/output split. Otherwise falls back to a blended `typical_usd_per_call`.
3. **Task complexity filter**: `task_complexity` (`low`/`medium`/`high`/`very_high`) filters the provider's model catalog to variants capable of the task. A `very_high` task on Anthropic picks Opus; a `low` task picks Haiku.
4. **Strategy weights** (locked in 2026-04-15, rows sum to 1.0):
   - `reliability_first`: (0.80 reliability, 0.20 cost, 0.00 latency)
   - `balanced`: (0.55, 0.45, 0.00)
   - `cost_first`: (0.25, 0.75, 0.00)
   - `speed_first`: (0.35, 0.45, 0.20) — third axis normalized against category-median latency
5. **Model selection within provider**: once the capable pool is filtered, the strategy decides. `cost_first` → cheapest capable, `speed_first` → lowest latency capable, `reliability_first` → most capable (hedge toward power), `balanced` → combined cost + latency + tier penalty.
6. **Within-budget flag, never filtered**: tools exceeding `max_price_per_call` or `max_monthly_budget` are returned with `within_budget: false` and a `budget_explanation` string, never silently filtered. Agents see the best match regardless of budget so they can decide to relax caps or pick an alternative.
7. **Reasoning string**: every response carries a human-readable `reasoning` field describing the decision — reliability score, recommended model, cost, latency, strategy, task complexity, and budget fit. Drop it straight into agent logs.

### LLM providers with full model catalogs

| Provider | Models in catalog | Typical latency |
|---|---|---|
| `api.anthropic.com/v1/messages` | claude-haiku-4-5 (low), claude-sonnet-4-6 (medium), claude-opus-4-6 (very_high) | 500 – 2500 ms |
| `api.openai.com/v1/chat/completions` | gpt-4o-mini (low), gpt-4o (medium), o3-mini (high) | 500 – 4500 ms |
| `api.groq.com/openai/v1/chat/completions` | llama-3.1-8b-instant (low), llama-3.3-70b-versatile (medium) | 200 – 400 ms |
| `api.together.xyz/v1/chat/completions` | llama-3.1-8b-instruct-turbo (low), llama-3.3-70b-instruct-turbo (medium), DeepSeek-V3 (high) | 400 – 1500 ms |
| `api.mistral.ai/v1/chat/completions` | mistral-small-latest (low), mistral-large-latest (medium) | 600 – 1000 ms |
| `api.deepseek.com/v1/chat/completions` | deepseek-chat (medium), deepseek-reasoner (very_high) | 1500 – 5000 ms |

### Drop-in Python class

A fully-documented `LLMRouter` class lives at [`sdks/python/examples/llm_router.py`](https://github.com/netvistamedia/toolrate/blob/main/sdks/python/examples/llm_router.py). It assesses all six providers in parallel via `asyncio.gather`, picks the winner, dispatches through a subclassable `_dispatch()` hook, falls back to the next-best candidate on failure, and reports every outcome back to `/v1/report` so the scoring loop self-corrects.

```python
import asyncio
from toolrate import AsyncToolRate
from llm_router import LLMRouter  # the example class

class MyRouter(LLMRouter):
    async def _dispatch(self, decision, prompt):
        # Wire up your preferred provider SDK using decision.provider
        # and decision.model. See the example file for a full version.
        ...

async def main():
    async with AsyncToolRate(api_key="nf_live_...") as tr:
        router = MyRouter(
            tr,
            max_price_per_call=0.01,
            expected_calls_per_month=50_000,
        )
        result = await router.route(
            prompt="Summarize this meeting transcript in 3 bullets.",
            task_complexity="medium",
            expected_tokens=1500,
            budget_strategy="balanced",
        )
        print(result["response"])
        print(result["routing"])  # RoutingDecision dataclass

asyncio.run(main())
```

## Key Facts

- **__LANDING_TOOLS_COUNT__ tools rated** across payment, email, storage, AI, and more
- **__LANDING_REPORTS_COUNT__ data points** from real agent executions
- **6 LLM providers** with full model catalogs for the Cost-Aware Router (Anthropic, OpenAI, Groq, Together, Mistral, DeepSeek)
- **<8ms average response time**
- **10 LLM sources** contributing assessment data
- **GDPR compliant**, hosted in Germany (Hetzner Cloud)
- **Open source**: https://github.com/netvistamedia/toolrate
"""

ROBOTS_TXT_APEX = """# ToolRate — https://toolrate.ai
# Canonical marketing + content host. Serves the landing page, pricing,
# demo, register, privacy, llms.txt / llms-full.txt / llms/toolrate-*.md,
# and the sitemap. The JSON API endpoints live on api.toolrate.ai.
User-agent: *
Allow: /
Disallow: /v1/
Disallow: /billing/
Disallow: /dashboard
Disallow: /me
Disallow: /upgrade

# llmstxt.org entry points
# /llms.txt — short index, 41 languages
# /llms-full.txt — full English reference
# /llms/toolrate-<lang>.md — one file per language

Sitemap: https://toolrate.ai/sitemap.xml
"""

ROBOTS_TXT_API = """# ToolRate API — https://api.toolrate.ai
# Developer-facing API host. Only the API docs (/docs, /redoc,
# /openapi.json) are meant to be indexed here. All marketing paths are
# 301-redirected to https://toolrate.ai — crawlers should follow the
# redirects and index those there. The canonical sitemap lives on apex.
User-agent: *
Allow: /docs
Allow: /redoc
Allow: /openapi.json
Disallow: /v1/
Disallow: /
"""

# Legacy alias — keep until everything imports the new names.
ROBOTS_TXT = ROBOTS_TXT_APEX
