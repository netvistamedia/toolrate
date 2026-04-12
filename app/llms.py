"""LLM-readable site content — llms.txt and llms-full.txt (llmstxt.org standard)."""

LLMS_TXT = """# ToolRate

> Reliability oracle for AI agents. Rates 600+ tools and APIs so agents pick the right one from the start.

ToolRate provides real-time reliability scores for external tools and APIs, based on the collective experience of thousands of AI agents. Before your agent calls a tool, check ToolRate to get a reliability score, failure risk, common pitfalls, and alternatives.

## Docs

- [API Documentation](https://api.toolrate.ai/docs): Interactive Swagger UI with all endpoints
- [API Reference](https://api.toolrate.ai/redoc): Full OpenAPI reference documentation
- [GitHub](https://github.com/netvistamedia/toolrate): Source code and examples
- [Get API Key](https://toolrate.ai/register): Free tier — 100 calls/day, no credit card required

## SDKs

- Python: `pip install nemoflow`
- TypeScript: `npm install nemoflow`

## API Base URL

https://toolrate.ai

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

> Reliability oracle for AI agents. Rates 600+ tools and APIs so agents pick the right one from the start.

ToolRate provides real-time reliability scores for external tools and APIs, based on the collective experience of thousands of AI agents. Before your agent calls a tool, check ToolRate to get a reliability score, failure risk, common pitfalls, and alternatives. The data moat grows with every report, making scores more accurate for everyone.

## API Base URL

https://toolrate.ai

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
pip install nemoflow
```

```python
from nemoflow import NemoFlowClient, guard

client = NemoFlowClient("nf_live_...")

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
npm install nemoflow
```

```typescript
import { NemoFlowClient } from "nemoflow";

const client = new NemoFlowClient("nf_live_...");

const score = await client.assess("https://api.stripe.com/v1/charges");

const result = await client.guard(
  "https://api.stripe.com/v1/charges",
  () => stripe.charges.create({...}),
  { fallbacks: [
    ["https://api.lemonsqueezy.com/v1/checkouts",
     () => lemon.createCheckout({...})],
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
  "tool_identifier": "https://api.stripe.com/v1/charges",
  "reliability_score": 94.2,
  "confidence": 0.87,
  "failure_risk": "low",
  "sample_size": 1240,
  "pitfalls": ["Rate limit 429 errors above 100 req/s", "Requires idempotency key for retries"],
  "alternatives": [
    {
      "tool_identifier": "https://api.lemonsqueezy.com/v1/checkouts",
      "reliability_score": 91.5,
      "fallback_success_rate": 0.89
    }
  ],
  "recommendation": "safe_to_call"
}
```

The `recommendation` field can be: `safe_to_call`, `use_with_caution`, `consider_alternative`, or `avoid`.

---

### POST /v1/report

Report execution result (success or failure). This builds the community data moat. Requires API key.

**Request body:**
```json
{
  "tool_identifier": "https://api.stripe.com/v1/charges",
  "success": true,
  "latency_ms": 420,
  "error_category": null,
  "error_message": null,
  "metadata": {}
}
```

For failures, include `error_category` (e.g., "timeout", "auth_failure", "rate_limit", "server_error") and optionally `error_message`.

**Response (201):**
```json
{
  "accepted": true,
  "tool_identifier": "https://api.stripe.com/v1/charges",
  "updated_score": 94.1
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
      "tool_identifier": "https://api.resend.com/emails",
      "reliability_score": 96.8,
      "fallback_success_rate": 0.94,
      "category": "email",
      "times_used_as_fallback": 342
    }
  ]
}
```

---

### GET /v1/discover/fallback-chain

Get the best alternatives when a tool fails, based on real agent journey data. Requires API key.

**Query parameters:**
- `tool_identifier` (required): The tool to find alternatives for
- `limit` (optional): Number of alternatives (default 5)

**Response (200):**
```json
{
  "tool_identifier": "https://api.stripe.com/v1/charges",
  "fallback_chain": [
    {
      "tool_identifier": "https://api.lemonsqueezy.com/v1/checkouts",
      "reliability_score": 91.5,
      "fallback_success_rate": 0.89,
      "avg_switch_count": 1.2
    }
  ]
}
```

---

### GET /v1/tools

Search and browse all rated tools. Requires API key.

**Query parameters:**
- `category` (optional): Filter by category
- `search` (optional): Search by tool name or identifier
- `min_score` (optional): Minimum reliability score
- `limit` (optional): Number of results (default 20)
- `offset` (optional): Pagination offset

---

### GET /v1/tools/categories

List all tool categories with counts. Requires API key.

**Response (200):**
```json
{
  "categories": [
    {"name": "payment", "count": 45},
    {"name": "email", "count": 32},
    {"name": "storage", "count": 28}
  ]
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
  "total_tools": 637,
  "total_reports": 68400,
  "total_assessments": 142000,
  "avg_reliability": 82.1
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
