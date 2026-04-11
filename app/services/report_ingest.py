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

    # Invalidate cache
    tool_id_str = str(tool.id)
    await redis.delete(f"score:{tool_id_str}:{ctx_hash}:{data_pool or ''}")
    await redis.delete(f"score:{tool_id_str}:__global__:{data_pool or ''}")

    return tool, report
