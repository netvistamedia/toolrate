<p align="center">
  <img src="https://toolrate.ai/toolrate-logo.webp" alt="ToolRate" width="80">
</p>

<h1 align="center">ToolRate</h1>

<p align="center">
  <strong>Stop your AI agents from calling tools that are about to fail.</strong>
</p>

<p align="center">
  <a href="https://toolrate.ai">API</a> &nbsp;|&nbsp;
  <a href="https://api.toolrate.ai/docs">Docs</a> &nbsp;|&nbsp;
  <a href="https://toolrate.ai/register">Get API Key</a>
</p>

---

ToolRate is a reliability oracle for AI agents. It scores 600+ tools and APIs in real time so your agent picks the right one *before* wasting a call on a failing endpoint. One line wraps any tool call with assess-before, report-after, and automatic fallback.

## The problem

AI agents fail **60-80% of the time** on external tool calls. Timeouts, rate limits, auth failures, flaky APIs. Your agent retries blindly, burns tokens, and still fails. ToolRate gives it the information it needs to make smarter choices.

## One line of code

**Python**

```python
from toolrate import ToolRate, guard

client = ToolRate("nf_live_...")

result = guard(client, "https://api.openai.com/v1/chat/completions",
               lambda: openai.chat.completions.create(model="gpt-4", messages=msgs))
```

**TypeScript**

```typescript
import { ToolRate } from "toolrate";

const client = new ToolRate("nf_live_...");

const result = await nemo.guard(
  "https://api.openai.com/v1/chat/completions",
  () => openai.chat.completions.create({ model: "gpt-4", messages }),
);
```

`guard()` automatically assesses reliability before calling, executes the tool, reports the outcome, and on failure tries your fallback tools.

## What you get back

```json
{
  "reliability_score": 94.2,
  "confidence": 0.87,
  "historical_success_rate": "89% (last 30 days, 12k calls)",
  "predicted_failure_risk": "low",
  "common_pitfalls": [
    "timeout (8% of failures)",
    "rate_limit (3% of failures)"
  ],
  "recommended_mitigations": [
    "Increase timeout to 30s; implement retry with exponential backoff",
    "Add request throttling; use credential rotation if available"
  ],
  "top_alternatives": [
    {
      "tool": "https://api.lemonsqueezy.com/v1/checkouts",
      "score": 97.1,
      "reason": "Alternative provider"
    }
  ],
  "estimated_latency_ms": 420,
  "last_updated": "2026-04-11T09:05:00Z"
}
```

A single call gives your agent a reliability score, failure risk, common pitfalls, mitigations, and ranked alternatives -- everything it needs to decide whether to proceed, retry, or switch tools.

## Install

```bash
pip install toolrate        # Python
npm install toolrate        # TypeScript / Node.js
```

## Quickstart

**1. Get an API key** (free, no credit card):

```
https://toolrate.ai/register
```

**2. Assess a tool:**

```python
from toolrate import ToolRate

client = ToolRate("nf_live_...")
score = client.assess("https://api.stripe.com/v1/charges", context="e-commerce checkout")
print(score["reliability_score"])  # 94.2
```

**3. Report outcomes** (builds the data moat):

```python
client.report("https://api.stripe.com/v1/charges", success=True, latency_ms=420)
```

**4. Use guard() with auto-fallback:**

```python
result = guard(client, "https://api.openai.com/v1/chat/completions",
    lambda: openai.chat.completions.create(...),
    min_score=50,
    fallbacks=[
        ("https://api.anthropic.com/v1/messages",
         lambda: anthropic.messages.create(...)),
        ("https://api.groq.com/openai/v1/chat/completions",
         lambda: groq.chat.completions.create(...)),
    ])
```

If the primary tool's score is below `min_score`, guard skips straight to the highest-scoring fallback. If execution fails, it automatically tries the next one.

## Features

| Feature | Description |
|---------|-------------|
| **Reliability scoring** | Bayesian-smoothed, recency-weighted scores for 600+ tools. New tools start at ~83% and converge after ~25 reports. |
| **guard() wrapper** | One-line wrapper that assesses, executes, reports, and falls back automatically. Available in Python and TypeScript. |
| **On-demand LLM assessment** | Unknown tool? ToolRate uses Claude Sonnet to generate an instant reliability assessment from 10 LLM sources. |
| **Hidden gems** | Discover tools that are rarely the first choice but consistently succeed as fallbacks. |
| **Fallback chains** | See what agents actually switch to when a tool fails, ranked by success rate. |
| **Webhooks** | Get notified when a tool's reliability score changes significantly. |
| **MCP server** | Works with Claude Code and Cursor as an MCP tool provider. |
| **Journey tracking** | Track multi-step agent sessions with `session_id` and `attempt_number` to build fallback intelligence. |
| **GDPR compliant** | Hosted in Germany (Hetzner, Nuremberg). Only hashes stored, no payloads. |

## How scoring works

1. **Recency-weighted average** -- 70% weight on last 7 days (exponential decay, half-life 3.5 days)
2. **Bayesian smoothing** -- new tools start at ~83%, converge to real performance after ~25 reports
3. **Context bucketing** -- different scores for different workflow contexts
4. **Trend detection** -- failure risk adjusts if last 24h is worse than the 7-day average
5. **Error aggregation** -- common pitfalls ranked by frequency across all reports

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/assess` | Get reliability score, pitfalls, and alternatives |
| `POST` | `/v1/report` | Report tool execution outcome |
| `GET`  | `/v1/discover/hidden-gems` | Find high-success fallback tools |
| `GET`  | `/v1/discover/fallback-chain` | Best alternatives when a tool fails |
| `GET`  | `/v1/tools` | Search and browse tools by category |
| `POST` | `/v1/webhooks` | Register score change webhooks |
| `POST` | `/v1/auth/register` | Get a free API key |
| `GET`  | `/v1/stats` | Platform metrics |

All endpoints (except register and health) require an `X-Api-Key` header.

Full interactive documentation: **[api.toolrate.ai/docs](https://api.toolrate.ai/docs)**

## Pricing

| Tier | Rate limit | Price |
|------|-----------|-------|
| Free | 100 calls/day | $0 |
| Pro | 10,000 calls/day | $29/mo |
| Enterprise | Custom | [Contact us](https://toolrate.ai) |

## Stack

Python 3.12 / FastAPI / PostgreSQL / Redis / Caddy / Docker -- hosted on Hetzner Cloud in Germany.

## License

Proprietary. Contact for licensing.
