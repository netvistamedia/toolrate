import hashlib

from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import ExecutionReport
from app.models.tool import Tool


def _context_hash(context: str) -> str:
    if not context:
        return "__global__"
    return hashlib.sha256(context.encode()).hexdigest()[:16]


async def upsert_tool(db: AsyncSession, identifier: str) -> Tool:
    """Get or create a tool by identifier."""
    result = await db.execute(select(Tool).where(Tool.identifier == identifier))
    tool = result.scalar_one_or_none()
    if tool:
        return tool

    tool = Tool(identifier=identifier)
    db.add(tool)
    await db.flush()
    return tool


async def ingest_report(
    db: AsyncSession,
    redis: Redis,
    tool_identifier: str,
    success: bool,
    error_category: str | None,
    latency_ms: int | None,
    context: str,
    reporter_fingerprint: str,
    data_pool: str | None = None,
    session_id: str | None = None,
    attempt_number: int | None = None,
    previous_tool: str | None = None,
) -> tuple[Tool, ExecutionReport]:
    tool = await upsert_tool(db, tool_identifier)
    ctx_hash = _context_hash(context)

    report = ExecutionReport(
        tool_id=tool.id,
        success=success,
        error_category=error_category,
        latency_ms=latency_ms,
        context_hash=ctx_hash,
        reporter_fingerprint=reporter_fingerprint,
        data_pool=data_pool,
        session_id=session_id,
        attempt_number=attempt_number,
        previous_tool=previous_tool,
    )
    db.add(report)

    # Increment tool report count
    await db.execute(
        update(Tool).where(Tool.id == tool.id).values(report_count=Tool.report_count + 1)
    )

    await db.commit()

    # Invalidate cache and check for webhook-worthy score changes
    tool_id_str = str(tool.id)
    global_cache_key = f"score:{tool_id_str}:__global__:{data_pool or ''}"

    # Read old score before invalidating
    old_score_raw = await redis.get(global_cache_key)
    old_score = None
    if old_score_raw:
        import json
        try:
            old_score = json.loads(old_score_raw).get("reliability_score")
        except (json.JSONDecodeError, AttributeError):
            pass

    await redis.delete(f"score:{tool_id_str}:{ctx_hash}:{data_pool or ''}")
    await redis.delete(global_cache_key)

    # Dispatch webhooks if score changed significantly
    if old_score is not None:
        from app.services.scoring import compute_score
        new_response = await compute_score(db, tool, "__global__", data_pool)
        new_score = new_response.reliability_score
        if abs(new_score - old_score) >= 1:
            from app.services.webhook_dispatch import dispatch_score_change
            await dispatch_score_change(db, tool_identifier, old_score, new_score)

    return tool, report
