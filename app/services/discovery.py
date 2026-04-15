"""Discovery service — find hidden gem tools based on fallback patterns.

Analyzes agent journey data to find tools that:
1. Are rarely the first choice (low attempt_number=1 count)
2. Have high success rates as fallbacks (attempt_number >= 2)
3. Succeed where popular tools failed (previous_tool data)

Both queries filter out synthetic bootstrap reports (seed.py, llm_ondemand,
llm_consensus) so only real agent journeys contribute — otherwise an LLM
that was primed into the DB at launch would show up as a "hidden gem"
without a single real user ever having tried it. They also apply Bayesian
smoothing on the ranking so a tool with 3/3 successes does not outrank a
tool with 95/100 — an unreasonable recommendation given the sample sizes.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.report import ExecutionReport
from app.models.tool import Tool
# Re-use the set scoring.py uses so "synthetic" has exactly one definition
# across the codebase. Importing through the underscore is intentional —
# this is an internal cross-service constant, not a public API.
from app.services.scoring import _LLM_SYNTHETIC_FINGERPRINTS


def _smoothed_rate_expr(success_col):
    """Build a SQL expression that Bayesian-smooths a success rate.

    Prior (α=5, β=1 by default) matches the scoring algorithm, so a tool
    with zero history evaluates to ~83% — the same cold-start number
    `/v1/assess` returns. With N=3 perfect successes the posterior mean
    is (3+5)/(3+6) ≈ 88.9%, which correctly ranks BELOW a tool with
    95/100 at (95+5)/(100+6) ≈ 94.3%. The raw success rate is still
    returned in the response for display; the smoothed value is only
    used for ORDER BY so bookmarkable links don't break.
    """
    alpha = settings.bayesian_alpha_prior
    beta = settings.bayesian_beta_prior
    success_count = func.sum(case((success_col == True, 1), else_=0))  # noqa: E712
    total_count = func.count()
    return (success_count + alpha) / (total_count + alpha + beta)


async def get_hidden_gems(
    db: AsyncSession,
    category: str | None = None,
    context_hash: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Find tools that shine as fallbacks — high success rate when tried as 2nd+ choice."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    raw_rate = func.avg(case((ExecutionReport.success == True, 1.0), else_=0.0))  # noqa: E712
    smoothed_rate = _smoothed_rate_expr(ExecutionReport.success)

    query = (
        select(
            ExecutionReport.tool_id,
            Tool.identifier,
            Tool.display_name,
            Tool.category,
            func.count().label("fallback_count"),
            raw_rate.label("fallback_success_rate"),
            func.avg(ExecutionReport.latency_ms).label("avg_latency"),
        )
        .join(Tool, ExecutionReport.tool_id == Tool.id)
        .where(
            ExecutionReport.attempt_number >= 2,
            ExecutionReport.created_at >= cutoff,
            # Exclude LLM bootstrap reports — they describe model consensus,
            # not real agent behaviour, and have no business driving a
            # "real agent journey data" recommendation surface.
            ExecutionReport.reporter_fingerprint.notin_(_LLM_SYNTHETIC_FINGERPRINTS),
        )
        .group_by(ExecutionReport.tool_id, Tool.identifier, Tool.display_name, Tool.category)
        .having(func.count() >= 3)  # Need at least 3 fallback uses
        .order_by(smoothed_rate.desc())
        .limit(limit)
    )

    if category:
        query = query.where(Tool.category == category)

    result = await db.execute(query)
    rows = result.all()

    gems = []
    for row in rows:
        gems.append({
            "tool": row.identifier,
            "display_name": row.display_name,
            "category": row.category,
            "fallback_success_rate": round(float(row.fallback_success_rate) * 100, 1),
            "times_used_as_fallback": row.fallback_count,
            "avg_latency_ms": round(float(row.avg_latency)) if row.avg_latency else None,
        })

    return gems


async def get_fallback_chains(
    db: AsyncSession,
    tool_identifier: str,
    limit: int = 5,
) -> list[dict]:
    """For a given tool, find what agents typically switch TO when it fails."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    raw_rate = func.avg(case((ExecutionReport.success == True, 1.0), else_=0.0))  # noqa: E712
    smoothed_rate = _smoothed_rate_expr(ExecutionReport.success)

    query = (
        select(
            Tool.identifier,
            Tool.display_name,
            func.count().label("times_chosen"),
            raw_rate.label("success_rate"),
            func.avg(ExecutionReport.latency_ms).label("avg_latency"),
        )
        .join(Tool, ExecutionReport.tool_id == Tool.id)
        .where(
            ExecutionReport.previous_tool == tool_identifier,
            ExecutionReport.created_at >= cutoff,
            # Synthetic bootstrap reports never describe a real fallback —
            # seed.py and llm_*.py don't populate previous_tool, but the
            # explicit filter is cheap defence-in-depth if that ever changes.
            ExecutionReport.reporter_fingerprint.notin_(_LLM_SYNTHETIC_FINGERPRINTS),
        )
        .group_by(Tool.identifier, Tool.display_name)
        .having(func.count() >= 2)
        .order_by(smoothed_rate.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    chains = []
    for row in rows:
        chains.append({
            "fallback_tool": row.identifier,
            "display_name": row.display_name,
            "times_chosen_after_failure": row.times_chosen,
            "success_rate": round(float(row.success_rate) * 100, 1),
            "avg_latency_ms": round(float(row.avg_latency)) if row.avg_latency else None,
        })

    return chains
