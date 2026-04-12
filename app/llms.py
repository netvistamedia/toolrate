"""LLM-readable site content — llms.txt and llms-full.txt (llmstxt.org standard)."""

LLMS_TXT = """# ToolRate

> Real advice for every tool your agent considers. Objective, crowdsourced reliability ratings and actionable intelligence for 600+ tools and APIs, based on thousands of real agent executions across production workloads.

ToolRate delivers real-time reliability scores, failure risk, jurisdiction intelligence, common pitfalls, and smart alternatives for every external tool your agent calls. Know before you call. Choose correctly the first time.

## Docs

- [API Documentation](https://api.toolrate.ai/docs): Interactive Swagger UI with all endpoints
- [API Reference](https://api.toolrate.ai/redoc): Full OpenAPI reference documentation
- [GitHub](https://github.com/netvistamedia/toolrate): Source code and examples
- [Get API Key](https://toolrate.ai/register): Free tier — 100 calls/day, no credit card required

## SDKs

- Python: `pip install toolrate`
- TypeScript: `npm install toolrate`

## API Base URL

https://api.toolrate.ai

## Authentication

All API endpoints require an API key via the `X-Api-Key` header.

## Core Endpoints

- [POST /v1/assess](https://api.toolrate.ai/docs#/Assessment/assess_tool_v1_assess_post): Get reliability score for a tool before calling it
- [POST /v1/report](https://api.toolrate.ai/docs#/Reporting/report_result_v1_report_post): Report execution result (success/failure) to build the data moat
- [GET /v1/discover/hidden-gems](https://api.toolrate.ai/docs#/Discovery): Find tools with high fallback success rates
- [GET /v1/discover/fallback-chain](https://api.toolrate.ai/docs#/Discovery): Get best alternatives when a tool fails
- [GET /v1/tools](https://api.toolrate.ai/docs#/Tools): Search and browse all rated tools
- [GET /v1/tools/categories](https://api.toolrate.ai/docs#/Tools): List all tool categories

## Optional

- [Full documentation for LLMs](https://toolrate.ai/llms-full.txt)
"""

LLMS_FULL_TXT = """# ToolRate — Full Documentation for LLMs

> Real advice for every tool your agent considers. Objective, crowdsourced reliability ratings and actionable intelligence for 600+ tools and APIs, based on thousands of real agent executions across production workloads.

ToolRate delivers real-time reliability scores, failure risk, jurisdiction intelligence, common pitfalls, and smart alternatives for every external tool your agent calls. Each assessment is timestamped and ships with a confidence interval and per-error-category breakdown, so agents, developers, and enterprise compliance teams all get the same objective view. Know before you call. Choose correctly the first time. The data pool grows with every report, making the intelligence sharper for everyone.

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

```bash
pip install toolrate
```

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

Get a reliability score for a tool before calling it. Requires API key.

**Request body:**
```json
{
  "tool_identifier": "https://api.stripe.com/v1/charges",
  "context": "payment processing for e-commerce checkout"
}
```

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
    {"tool": "https://api.lemonsqueezy.com/v1/checkouts", "score": 91.5, "reason": "Alternative provider"}
  ],
  "estimated_latency_ms": 420,
  "latency": {"avg": 420, "p50": 380, "p95": 890, "p99": 1200},
  "last_updated": "2026-04-11T09:05:00Z",
  "hosting_jurisdiction": "Non-EU (United States)",
  "gdpr_compliant": false,
  "data_residency_risk": "medium",
  "recommended_for": ["general_purpose"],
  "eu_alternatives": []
}
```

`predicted_failure_risk` can be: `low`, `medium`, `high`, or `unknown`.
`data_source` is one of `empirical`, `llm_estimated`, or `bayesian_prior`.

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

## Key Facts

- **637+ tools rated** across payment, email, storage, AI, and more
- **68,400+ data points** from real agent executions
- **<8ms average response time**
- **10 LLM sources** contributing assessment data
- **GDPR compliant**, hosted in Germany (Hetzner Cloud)
- **Open source**: https://github.com/netvistamedia/toolrate
"""

ROBOTS_TXT = """# ToolRate — https://toolrate.ai
User-agent: *
Allow: /
Disallow: /v1/
Disallow: /billing/

# LLM-specific content
# See https://llmstxt.org
Sitemap: https://toolrate.ai/sitemap.xml
"""
