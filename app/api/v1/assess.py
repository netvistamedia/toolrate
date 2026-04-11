import hashlib
import uuid as _uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.config import settings
from app.dependencies import Db, RedisClient, AuthenticatedKey
from app.models.tool import Tool
from app.schemas.assess import AssessRequest, AssessResponse
from app.services.cache import get_cached_score, set_cached_score
from app.services.scoring import compute_score

router = APIRouter()


def _context_hash(context: str) -> str:
    if not context:
        return "__global__"
    return hashlib.sha256(context.encode()).hexdigest()[:16]


@router.post("/assess", response_model=AssessResponse, tags=["Assessment"],
             summary="Assess tool reliability",
             description="Get a real-time reliability score for any external tool or API before calling it. "
                         "Returns reliability score, confidence, failure risk, common pitfalls, mitigations, and alternatives.")
async def assess_tool(
    body: AssessRequest,
    db: Db,
    redis: RedisClient,
    api_key: AuthenticatedKey,
):
    ctx_hash = _context_hash(body.context)
    data_pool = api_key.data_pool

    # Resolve tool identifier
    tool_cache_key = f"tool:{body.tool_identifier}"
    cached_tool_id = await redis.get(tool_cache_key)

    if cached_tool_id:
        result = await db.execute(select(Tool).where(Tool.id == _uuid.UUID(cached_tool_id)))
        tool = result.scalar_one_or_none()
    else:
        result = await db.execute(
            select(Tool).where(Tool.identifier == body.tool_identifier)
        )
        tool = result.scalar_one_or_none()
        if tool:
            await redis.set(tool_cache_key, str(tool.id), ex=3600)

    # If tool doesn't exist, return cold start response
    if not tool:
        return compute_score.__wrapped__ if False else await _cold_start(body, db, redis, ctx_hash, data_pool)

    # Check cache
    cached = await get_cached_score(redis, str(tool.id), ctx_hash, data_pool)
    if cached:
        return cached

    # Compute score
    response = await compute_score(db, tool, ctx_hash, data_pool)

    # Cache it
    ttl = settings.cache_ttl_hot if tool.report_count >= settings.hot_threshold_reports_7d else settings.cache_ttl_cold
    await set_cached_score(redis, str(tool.id), ctx_hash, data_pool, response, ttl)

    return response


async def _cold_start(body: AssessRequest, db: Db, redis: RedisClient, ctx_hash: str, data_pool: str | None):
    """Handle assessment for unknown tools — try LLM assessment, fall back to Bayesian prior."""
    from app.services.report_ingest import upsert_tool
    from app.services.scoring import _cold_start_response, compute_score
    from app.services.llm_assess import assess_tool_with_llm, create_tool_from_assessment
    from datetime import datetime, timezone

    tool = await upsert_tool(db, body.tool_identifier)
    await db.commit()
    await redis.set(f"tool:{body.tool_identifier}", str(tool.id), ex=3600)

    # Try on-demand LLM assessment for an intelligent first response
    if settings.anthropic_api_key:
        assessment = await assess_tool_with_llm(body.tool_identifier)
        if assessment:
            await create_tool_from_assessment(db, tool, assessment)
            # Now compute a real score from the generated reports
            response = await compute_score(db, tool, ctx_hash, data_pool)
            await set_cached_score(redis, str(tool.id), ctx_hash, data_pool, response, settings.cache_ttl_cold)
            return response

    return _cold_start_response(datetime.now(timezone.utc))
