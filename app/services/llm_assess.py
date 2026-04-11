"""
On-demand LLM assessment for unknown tools.

When /v1/assess gets a tool we've never seen, instead of returning a generic
cold start score, we ask Claude to assess it in real time. The result is
cached and synthetic reports are generated so future queries are instant.
"""
import asyncio
import json
import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tool import Tool
from app.models.report import ExecutionReport
from app.core.security import make_fingerprint

logger = logging.getLogger("nemoflow.llm_assess")

ASSESS_PROMPT = """You are a senior DevOps engineer assessing API reliability for AI agents.

Assess this tool/API: {tool_identifier}

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
  "mitigations": ["Fix 1", "Fix 2", "Fix 3"]
}}

Rules:
- reliability_estimate: 0.0-1.0, probability a single API call succeeds
- common_errors frequencies must sum to 1.0 (distribution among failures)
- Error categories: timeout, rate_limit, server_error, auth_failure, validation_error, connection_error, not_found, permission_denied
- Be honest. If you don't recognize the tool, estimate conservatively (0.85-0.90).
- avg_latency_ms = estimated real-world P50 latency

Return ONLY the JSON object, no other text."""


async def assess_tool_with_llm(tool_identifier: str) -> dict | None:
    """Call Claude to assess an unknown tool. Returns parsed assessment or None on failure."""
    if not settings.anthropic_api_key:
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        # Run synchronous Anthropic call in thread pool
        msg = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": ASSESS_PROMPT.format(tool_identifier=tool_identifier),
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
    """Update tool metadata and generate synthetic reports from LLM assessment."""
    now = datetime.now(timezone.utc)
    fingerprint = make_fingerprint("llm_ondemand", "llm_ondemand")

    # Update tool metadata
    tool.display_name = assessment.get("display_name", tool.identifier)
    tool.category = assessment.get("category", "Other APIs")

    reliability = assessment.get("reliability_estimate", 0.9)
    avg_latency = assessment.get("avg_latency_ms", 500)
    errors = assessment.get("common_errors", [])

    # Generate synthetic reports (fewer than bulk import — just enough for scoring)
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
    await db.commit()

    logger.info(
        "LLM assessed %s: %s (reliability=%.2f, %d reports generated)",
        tool.identifier, assessment.get("display_name"), reliability, num_reports,
    )
