from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.identifiers import normalize_identifier
from app.core.security import context_hash as _context_hash
from app.models.report import ExecutionReport
from app.models.tool import Tool

# Atomic INCR+EXPIRE — same pattern as rate_limiter. Without this, a crash
# between INCR and EXPIRE leaves the fingerprint key with no TTL, so the
# per-tool-per-day counter never resets and the reporter is banned forever.
_INCR_WITH_TTL_LUA = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


async def upsert_tool(db: AsyncSession, identifier: str) -> Tool:
    """Get or create a tool by identifier. Handles concurrent inserts safely.

    Normalizes the identifier first so case/trailing-slash variants converge
    on a single ``tools`` row instead of fragmenting reports across two URLs
    that point at the same endpoint.
    """
    normalized = normalize_identifier(identifier)
    result = await db.execute(select(Tool).where(Tool.identifier == normalized))
    tool = result.scalar_one_or_none()
    if tool:
        return tool

    tool = Tool(identifier=normalized)
    db.add(tool)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        result = await db.execute(select(Tool).where(Tool.identifier == normalized))
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
    # Normalize previous_tool too so cross-tool fallback chain analytics
    # join on the same canonical identifier we use for the primary tool.
    previous_tool = normalize_identifier(previous_tool) if previous_tool else None
    tool = await upsert_tool(db, tool_identifier)
    ctx_hash = _context_hash(context)

    # Anti-gaming: limit reports per fingerprint per tool per day
    fp_key = f"fp:{reporter_fingerprint}:{tool.id}"
    fp_count = await redis.eval(_INCR_WITH_TTL_LUA, 1, fp_key, 86400)
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

    # Increment tool report count BEFORE flushing the report row so a
    # unique-constraint failure on (fingerprint, session, attempt) rolls
    # both writes back together and the counter doesn't tick up for a
    # rejected duplicate.
    await db.execute(
        update(Tool).where(Tool.id == tool.id).values(report_count=Tool.report_count + 1)
    )

    try:
        await db.flush()
    except IntegrityError:
        # Duplicate (fingerprint, session_id, attempt_number) — concurrent
        # report for the same agent journey step. Treat as idempotent
        # success: the first write already captured this attempt, return
        # the same tool the caller would have seen anyway.
        await db.rollback()
        return tool, None

    # Read old cached score BEFORE commit (avoids race with cache invalidation).
    # We read the __global__ bucket because that's what webhook score-change
    # comparisons are keyed on. Context-specific buckets can diverge freely.
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

    # Invalidate ALL cached score buckets for this tool — every context the
    # tool was ever assessed under would otherwise keep serving a stale score
    # until its TTL expires. Deleting only the reporter's current context
    # left every other caller staring at pre-report data for hours.
    pattern = f"score:{tool_id_str}:*"
    stale_keys = [key async for key in redis.scan_iter(match=pattern, count=100)]
    if stale_keys:
        await redis.delete(*stale_keys)

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
