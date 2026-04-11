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

ASSESS_PROMPT = """You are a senior DevOps engineer assessing API reliability for AI agents.

An AI agent wants to use this tool: {tool_identifier}
{context_line}

Assess this tool AND suggest up to 3 better or comparable alternatives that serve the same purpose. Alternatives should be real, production-ready APIs.

Return a JSON object with this exact structure:
{{
  "display_name": "Human-readable name",
  "category": "category (e.g. LLM APIs, Payment APIs, Email APIs, Developer Tools, etc.)",
  "reliability_estimate": 0.94,
  "avg_latency_ms": 450,
  "common_errors": [
    {{"category": "timeout", "frequency": 0.4}},
    {{"category": "rate_limit", "frequency": 0.35}},
    {{"category": "server_error", "frequency": 0.15}},
    {{"category": "auth_failure", "frequency": 0.1}}
  ],
  "pitfalls": ["Issue 1", "Issue 2", "Issue 3"],
  "mitigations": ["Fix 1", "Fix 2", "Fix 3"],
  "alternatives": [
    {{
      "identifier": "https://api.alternative.com/v1",
      "display_name": "Alternative Name",
      "reliability_estimate": 0.97,
      "reason": "Why this is a good alternative (e.g. higher uptime, lower latency, better rate limits)"
    }}
  ]
}}

Rules:
- reliability_estimate: 0.0-1.0, probability a single API call succeeds
- common_errors frequencies must sum to 1.0 (distribution among failures)
- Error categories: timeout, rate_limit, server_error, auth_failure, validation_error, connection_error, not_found, permission_denied
- Be honest. If you don't recognize the tool, estimate conservatively (0.85-0.90).
- avg_latency_ms = estimated real-world P50 latency
- alternatives: include ONLY if there are genuinely better or comparable options. Use real API base URLs.
- If the requested tool is already the best in its category, return an empty alternatives array.

Return ONLY the JSON object, no other text."""


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
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
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

        # Check if alternative link already exists
        result = await db.execute(
            select(Alternative).where(
                Alternative.tool_id == tool.id,
                Alternative.alternative_tool_id == alt_tool.id,
            )
        )
        if not result.scalar_one_or_none():
            alt_score = alt_data.get("reliability_estimate", 0.9)
            alt = Alternative(
                tool_id=tool.id,
                alternative_tool_id=alt_tool.id,
                relevance_score=alt_score,
            )
            db.add(alt)

    await db.commit()

    logger.info(
        "LLM assessed %s: %s (reliability=%.2f, %d reports, %d alternatives)",
        tool.identifier,
        assessment.get("display_name"),
        reliability,
        num_reports,
        len(alternatives),
    )
