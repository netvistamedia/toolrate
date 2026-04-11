"""Discovery service — find hidden gem tools based on fallback patterns.

Analyzes agent journey data to find tools that:
1. Are rarely the first choice (low attempt_number=1 count)
2. Have high success rates as fallbacks (attempt_number >= 2)
3. Succeed where popular tools failed (previous_tool data)
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import ExecutionReport
from app.models.tool import Tool


async def get_hidden_gems(
    db: AsyncSession,
    category: str | None = None,
    context_hash: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Find tools that shine as fallbacks — high success rate when tried as 2nd+ choice."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    # Find tools with fallback data (attempt_number >= 2 and success)
    query = (
        select(
            ExecutionReport.tool_id,
            Tool.identifier,
            Tool.display_name,
            Tool.category,
            # Total times used as fallback
            func.count().label("fallback_count"),
            # Success rate as fallback
            func.avg(case((ExecutionReport.success == True, 1.0), else_=0.0)).label("fallback_success_rate"),  # noqa: E712
            # Average latency
            func.avg(ExecutionReport.latency_ms).label("avg_latency"),
        )
        .join(Tool, ExecutionReport.tool_id == Tool.id)
        .where(
            ExecutionReport.attempt_number >= 2,
            ExecutionReport.created_at >= cutoff,
        )
        .group_by(ExecutionReport.tool_id, Tool.identifier, Tool.display_name, Tool.category)
        .having(func.count() >= 3)  # Need at least 3 fallback uses
        .order_by(func.avg(case((ExecutionReport.success == True, 1.0), else_=0.0)).desc())  # noqa: E712
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

    # Find reports where previous_tool matches and attempt succeeded
    query = (
        select(
            Tool.identifier,
            Tool.display_name,
            func.count().label("times_chosen"),
            func.avg(case((ExecutionReport.success == True, 1.0), else_=0.0)).label("success_rate"),  # noqa: E712
            func.avg(ExecutionReport.latency_ms).label("avg_latency"),
        )
        .join(Tool, ExecutionReport.tool_id == Tool.id)
        .where(
            ExecutionReport.previous_tool == tool_identifier,
            ExecutionReport.created_at >= cutoff,
        )
        .group_by(Tool.identifier, Tool.display_name)
        .having(func.count() >= 2)
        .order_by(func.avg(case((ExecutionReport.success == True, 1.0), else_=0.0)).desc())  # noqa: E712
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
