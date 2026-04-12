from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import context_hash as _context_hash
from app.models.report import ExecutionReport
from app.models.tool import Tool


async def upsert_tool(db: AsyncSession, identifier: str) -> Tool:
    """Get or create a tool by identifier. Handles concurrent inserts safely."""
    result = await db.execute(select(Tool).where(Tool.identifier == identifier))
    tool = result.scalar_one_or_none()
    if tool:
        return tool

    tool = Tool(identifier=identifier)
    db.add(tool)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        result = await db.execute(select(Tool).where(Tool.identifier == identifier))
        tool = result.scalar_one()
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
) -> tuple[Tool, ExecutionReport | None]:
    tool = await upsert_tool(db, tool_identifier)
    ctx_hash = _context_hash(context)

    # Anti-gaming: limit reports per fingerprint per tool per day
    fp_key = f"fp:{reporter_fingerprint}:{tool.id}"
    fp_count = await redis.incr(fp_key)
    if fp_count == 1:
        await redis.expire(fp_key, 86400)
    if fp_count > settings.max_reports_per_fingerprint_per_tool_per_day:
        return tool, None  # silently drop, don't reveal the limit

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

    # Read old cached score BEFORE commit (avoids race with cache invalidation)
    tool_id_str = str(tool.id)
    global_cache_key = f"score:{tool_id_str}:__global__:{data_pool or '__default__'}"
    old_score_raw = await redis.get(global_cache_key)
    old_score = None
    if old_score_raw:
        import json
        try:
            old_score = json.loads(old_score_raw).get("reliability_score")
        except (json.JSONDecodeError, AttributeError):
            pass

    await db.commit()

    # Invalidate cache
    await redis.delete(f"score:{tool_id_str}:{ctx_hash}:{data_pool or '__default__'}")
    await redis.delete(global_cache_key)

    # Dispatch webhooks if score changed significantly
    if old_score is not None:
        from app.services.scoring import compute_score
        await db.refresh(tool)
        new_response = await compute_score(db, tool, "__global__", data_pool)
        new_score = new_response.reliability_score
        if abs(new_score - old_score) >= 1:
            from app.services.webhook_dispatch import dispatch_score_change
            await dispatch_score_change(tool_identifier, old_score, new_score)

    return tool, report
