"""
On-demand LLM assessment for unknown tools.

When /v1/assess gets a tool we've never seen, instead of returning a generic
cold start score, we ask Claude to assess it in real time. The result is
cached and synthetic reports are generated so future queries are instant.

Also suggests better alternatives so every response has actionable value.
"""
import asyncio
import json
import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tool import Tool
from app.models.alternative import Alternative
from app.models.report import ExecutionReport
from app.core.security import make_fingerprint

logger = logging.getLogger("nemoflow.llm_assess")

ASSESS_PROMPT = """You are a senior site-reliability engineer rating an external API for an AI agent that's about to call it. Your output drives whether the agent calls this tool, retries, or switches to an alternative — so be precise and honest.

# Tool to assess
{tool_identifier}
{context_line}

# Your task
1. Identify the tool. If you do NOT recognize it (unfamiliar domain, no public docs you've seen), set "recognized": false and use conservative defaults — do NOT invent specific failure modes or alternatives.
2. Estimate real-world reliability based on what you know about the provider's track record, status pages, and common failure modes.
3. List 3-5 concrete failure modes paired with specific, actionable mitigations. Vague advice ("retry with backoff") is worthless — name the parameter ("exponential backoff starting at 500ms, max 30s, 5 attempts, jitter ±20%").
4. Suggest 0-3 real alternatives that solve the SAME problem the agent is solving (use the context). Only include alternatives you are confident actually exist as production APIs. If you cannot name real alternatives with high confidence, return an empty array — DO NOT invent URLs.

# Reliability calibration
- 0.98-1.00 — top-tier infrastructure (Stripe, AWS S3, Twilio core SMS, GitHub raw): >99.9% uptime, mature retry semantics, multi-region
- 0.94-0.97 — solid commercial API with occasional incidents (OpenAI, GitHub API, SendGrid, Anthropic)
- 0.88-0.93 — newer or single-region API, status page shows monthly incidents
- 0.80-0.87 — beta/community API, frequent rate limits, no published SLA
- below 0.80 — known unstable, or specific reasons to distrust it
- If "recognized": false → use 0.85 as conservative default and leave issues/alternatives sparse

# Mitigation quality bar
Each mitigation MUST be specific enough that a developer can implement it without further research. Include numbers, header names, status codes, retry intervals, or endpoint paths where relevant.

✅ GOOD: "Set request timeout to 60s on /v1/chat/completions; OpenAI's 99th-percentile response time exceeds 30s for gpt-4 with long contexts."
❌ BAD: "Use longer timeouts."

✅ GOOD: "Read the X-RateLimit-Remaining header on every response; pre-emptively pause when it drops below 10 to avoid the 429 cliff."
❌ BAD: "Handle rate limits gracefully."

# Output: a JSON object exactly matching this schema (no markdown, no commentary, no preamble)
{{
  "recognized": true,
  "display_name": "Stripe Payment Intents",
  "category": "Payment APIs",
  "reliability_estimate": 0.97,
  "avg_latency_ms": 380,
  "common_errors": [
    {{"category": "rate_limit", "frequency": 0.45}},
    {{"category": "validation_error", "frequency": 0.30}},
    {{"category": "timeout", "frequency": 0.15}},
    {{"category": "auth_failure", "frequency": 0.10}}
  ],
  "issues": [
    {{
      "category": "rate_limit",
      "pitfall": "Stripe enforces 100 read / 100 write requests per second per account in live mode; bursts return HTTP 429 with no Retry-After header.",
      "mitigation": "Implement a client-side token bucket at 80 req/s. On 429, back off exponentially starting at 500ms, max 30s, 5 attempts, with ±20% jitter to avoid thundering herds."
    }},
    {{
      "category": "validation_error",
      "pitfall": "Idempotency key collisions: replaying the same key with a different request body silently returns the original response, masking client bugs.",
      "mitigation": "Generate a fresh UUIDv4 idempotency key per logical operation. Set the Idempotency-Key header on every POST. Never reuse keys across retries that may carry different payloads."
    }},
    {{
      "category": "timeout",
      "pitfall": "PaymentIntent confirmation with 3DS authentication can take 5-15s end-to-end; the default 30s HTTP client timeout is too tight under load.",
      "mitigation": "Set request timeout to 60s on /v1/payment_intents/*/confirm. Prefer webhooks (payment_intent.succeeded) over polling for terminal status."
    }}
  ],
  "alternatives": [
    {{
      "identifier": "https://api.lemonsqueezy.com/v1/checkouts",
      "display_name": "Lemon Squeezy Checkouts",
      "reliability_estimate": 0.95,
      "reason": "Merchant-of-record handles VAT and global sales tax automatically — useful for SaaS selling internationally without registering for tax in every jurisdiction. Simpler API surface than Stripe but less flexible for complex billing."
    }},
    {{
      "identifier": "https://api.paddle.com/transactions",
      "display_name": "Paddle Transactions",
      "reliability_estimate": 0.94,
      "reason": "Also merchant-of-record; better than Lemon Squeezy for B2B SaaS thanks to built-in invoicing, dunning, and seat-based billing primitives."
    }}
  ]
}}

# Hard rules
- common_errors frequencies MUST sum to exactly 1.0 (rounded to 2 decimals).
- Error categories MUST be one of: timeout, rate_limit, server_error, auth_failure, validation_error, connection_error, not_found, permission_denied.
- "issues": 3-5 entries. Each "category" MUST match one of the categories listed in common_errors. Pitfalls and mitigations must be specific to THIS tool — generic API advice is rejected.
- "alternatives": 0-3 entries. Each identifier MUST be a real, currently-operating API base URL you are confident about. If unsure, omit it. The "reason" must explain WHY this alternative fits the agent's context (if provided).
- Output ONLY the JSON object. No markdown fences, no explanation, no preamble."""


async def assess_tool_with_llm(tool_identifier: str, context: str = "") -> dict | None:
    """Call Claude to assess an unknown tool with alternatives. Returns parsed assessment or None."""
    if not settings.anthropic_api_key:
        return None

    context_line = f"Context: the agent is using this for: {context}" if context else ""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        msg = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-6",
            max_tokens=2500,
            messages=[{
                "role": "user",
                "content": ASSESS_PROMPT.format(
                    tool_identifier=tool_identifier,
                    context_line=context_line,
                ),
            }],
        )

        text = msg.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]

        return json.loads(text)
    except Exception as e:
        logger.warning("LLM assessment failed for %s: %s", tool_identifier, e)
        return None


async def create_tool_from_assessment(
    db: AsyncSession,
    tool: Tool,
    assessment: dict,
):
    """Update tool metadata, generate synthetic reports, and store alternatives."""
    now = datetime.now(timezone.utc)
    fingerprint = make_fingerprint("llm_ondemand", "llm_ondemand")

    # Update tool metadata
    tool.display_name = assessment.get("display_name", tool.identifier)
    tool.category = assessment.get("category", "Other APIs")

    reliability = assessment.get("reliability_estimate", 0.9)
    avg_latency = assessment.get("avg_latency_ms", 500)
    errors = assessment.get("common_errors", [])

    # Persist tool-specific mitigations keyed by error category. scoring.py
    # prefers these over the generic MITIGATIONS dict, so the response shows
    # advice tailored to THIS tool instead of boilerplate.
    issues = assessment.get("issues", [])
    mitigations_by_cat: dict[str, str] = {}
    for issue in issues:
        cat = (issue.get("category") or "").strip()
        mit = (issue.get("mitigation") or "").strip()
        if cat and mit:
            # Last write wins if the LLM emits two issues for the same category.
            mitigations_by_cat[cat] = mit
    tool.mitigations_by_category = mitigations_by_cat or None

    # Generate synthetic reports
    num_reports = random.randint(30, 50)
    for _ in range(num_reports):
        age_days = random.uniform(0, 14)
        created_at = now - timedelta(days=age_days)
        success = random.random() < reliability
        latency = max(30, int(random.gauss(avg_latency, avg_latency * 0.3)))

        error_category = None
        if not success and errors:
            r = random.random()
            cumulative = 0.0
            for err in errors:
                cumulative += err.get("frequency", 0)
                if r <= cumulative:
                    error_category = err.get("category")
                    break
            if not error_category:
                error_category = errors[-1].get("category", "server_error")

        report = ExecutionReport(
            tool_id=tool.id,
            success=success,
            error_category=error_category,
            latency_ms=latency,
            context_hash="__global__",
            reporter_fingerprint=fingerprint,
            data_pool=None,
            created_at=created_at,
        )
        db.add(report)

    tool.report_count = num_reports

    # Store alternatives
    alternatives = assessment.get("alternatives", [])
    for alt_data in alternatives[:3]:
        alt_identifier = alt_data.get("identifier", "").strip()
        if not alt_identifier:
            continue

        # Find or create the alternative tool
        result = await db.execute(select(Tool).where(Tool.identifier == alt_identifier))
        alt_tool = result.scalar_one_or_none()
        if not alt_tool:
            alt_tool = Tool(
                identifier=alt_identifier,
                display_name=alt_data.get("display_name", alt_identifier),
                category=assessment.get("category", "Other APIs"),
            )
            db.add(alt_tool)
            await db.flush()
            # Enrich jurisdiction for the newly created alternative
            from app.services.jurisdiction import enrich_tool
            await enrich_tool(alt_tool)

        # Check if alternative link already exists
        result = await db.execute(
            select(Alternative).where(
                Alternative.tool_id == tool.id,
                Alternative.alternative_tool_id == alt_tool.id,
            )
        )
        existing = result.scalar_one_or_none()
        alt_reason = (alt_data.get("reason") or "").strip() or None
        if not existing:
            alt_score = alt_data.get("reliability_estimate", 0.9)
            alt = Alternative(
                tool_id=tool.id,
                alternative_tool_id=alt_tool.id,
                relevance_score=alt_score,
                reason=alt_reason,
            )
            db.add(alt)
        elif alt_reason and not existing.reason:
            # Backfill reason on links created before this column existed.
            existing.reason = alt_reason

    await db.commit()

    logger.info(
        "LLM assessed %s: %s (reliability=%.2f, %d reports, %d alternatives)",
        tool.identifier,
        assessment.get("display_name"),
        reliability,
        num_reports,
        len(alternatives),
    )
