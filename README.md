# NemoFlow

**The reliability oracle for AI agents.**

Before your agent calls an external tool, NemoFlow tells it: how reliable is this tool right now? What are the common pitfalls? What's a better alternative? After the call, your agent reports back — building a live data moat that makes every agent smarter.

**Live at [api.nemoflow.ai](https://api.nemoflow.ai)**

## Why

AI agents fail 60-80% of the time on external tool calls. Timeouts, rate limits, auth failures, flaky APIs. NemoFlow fixes this by giving agents real-time reliability intelligence before every call.

## One line of code

**Python:**
```python
from nemoflow import NemoFlowClient, guard

client = NemoFlowClient("nf_live_...")

result = guard(client, "https://api.openai.com/v1/chat/completions",
               lambda: openai.chat.completions.create(model="gpt-4", messages=msgs))
```

**TypeScript:**
```typescript
import { NemoFlow } from "nemoflow";
const nemo = new NemoFlow("nf_live_...");

const result = await nemo.guard(
  "https://api.openai.com/v1/chat/completions",
  () => openai.chat.completions.create({ model: "gpt-4", messages }),
);
```

This automatically:
- Checks the tool's reliability score before calling
- Executes the tool
- Reports success/failure (with auto error classification)
- On failure, tries fallback tools if configured

## Auto-fallback

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

## API

### POST /v1/assess

```bash
curl -X POST https://api.nemoflow.ai/v1/assess \
  -H "X-Api-Key: nf_live_..." \
  -H "Content-Type: application/json" \
  -d '{"tool_identifier": "https://api.stripe.com/v1/charges", "context": "e-commerce checkout"}'
```

```json
{
  "reliability_score": 94.2,
  "confidence": 0.87,
  "historical_success_rate": "89% (last 30 days, 12k calls)",
  "predicted_failure_risk": "low",
  "common_pitfalls": ["timeout (8% of failures)"],
  "recommended_mitigations": ["Increase timeout to 30s; implement retry with exponential backoff"],
  "top_alternatives": [{"tool": "https://api.lemonsqueezy.com/v1/checkouts", "score": 97.1}],
  "estimated_latency_ms": 420,
  "last_updated": "2026-04-11T09:05:00Z"
}
```

### POST /v1/report

```bash
curl -X POST https://api.nemoflow.ai/v1/report \
  -H "X-Api-Key: nf_live_..." \
  -H "Content-Type: application/json" \
  -d '{"tool_identifier": "https://api.stripe.com/v1/charges", "success": true, "latency_ms": 420}'
```

### GET /v1/discover/hidden-gems

Find tools that are rarely the first choice but have high success rates as fallbacks.

### GET /v1/discover/fallback-chain?tool_identifier=...

When a tool fails, what do agents typically switch to?

## SDKs

| SDK | Install | Docs |
|-----|---------|------|
| Python | `pip install nemoflow` | [sdks/python](sdks/python/) |
| TypeScript | `npm install nemoflow` | [sdks/typescript](sdks/typescript/) |

## Features

- **600+ tools** with reliability data from 9 LLM consensus sources
- **Real-time scoring** with Bayesian smoothing and recency weighting
- **<10ms** response on cache hit, <200ms on cache miss
- **Journey tracking** — track agent tool-calling sessions and fallback patterns
- **Hidden gems** — discover underrated tools with high fallback success rates
- **Auto-fallback** — guard() wrapper with automatic retry on better alternatives
- **GDPR compliant** — only hashes, no payloads stored

## How scoring works

1. **Recency-weighted average** — 70% weight on last 7 days (exponential decay, half-life 3.5 days)
2. **Bayesian smoothing** — new tools start at ~83% reliability, converge to actual performance after ~25 reports
3. **Context bucketing** — different scores for different workflow contexts
4. **Trend detection** — failure risk adjusts upward if last 24h is worse than 7d average

## Interactive docs

Visit [api.nemoflow.ai/docs](https://api.nemoflow.ai/docs) for the full OpenAPI documentation with try-it-out.

## Stack

- FastAPI + PostgreSQL + Redis
- Hosted on Hetzner Cloud (Nuremberg, DSGVO compliant)
- Auto-HTTPS via Caddy

## License

Proprietary. Contact for licensing.
