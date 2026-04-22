import asyncio
import logging
import uuid as _uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config import settings
from app.core.identifiers import normalize_identifier
from app.core.security import context_hash as _context_hash, effective_data_pool
from app.dependencies import Db, RedisClient, AuthenticatedKey
from app.models.tool import Tool
from app.schemas.assess import AssessRequest, AssessResponse
from app.services.cache import get_cached_score, set_cached_score
from app.services.payg_meter import record_assessment
from app.services.scoring import compute_score, finalize_response

logger = logging.getLogger("nemoflow.assess")
router = APIRouter()


async def _finalize_with_body(
    response: AssessResponse,
    db,
    tool: Tool | None,
    body: AssessRequest,
) -> AssessResponse:
    """Apply cost-aware augmentation using the request's budget params.

    Thin wrapper around scoring.finalize_response so the five call sites
    (cache hit / cache miss / three cold-start branches) stay terse and
    share the single source of truth for which body fields feed into the
    budget math and LLM-router augmentation.
    """
    return await finalize_response(
        response,
        db,
        tool,
        max_price_per_call=body.max_price_per_call,
        max_monthly_budget=body.max_monthly_budget,
        expected_calls_per_month=body.expected_calls_per_month,
        expected_tokens=body.expected_tokens,
        task_complexity=body.task_complexity,
        budget_strategy=body.budget_strategy,
    )


class BatchAssessItem(BaseModel):
    tool_identifier: str = Field(..., max_length=512)
    context: str = Field("", max_length=1024)


class BatchAssessRequest(BaseModel):
    tools: list[BatchAssessItem] = Field(..., min_length=1, max_length=20,
                                         description="Up to 20 tools to assess in parallel")


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
    # Billable unit — record first so PAYG overage metering is counted even
    # on cached responses (the agent still got a valid score).
    await record_assessment(redis, api_key)

    # Normalize the inbound identifier so e.g.
    # ``https://API.Stripe.com/v1/charges/`` and ``https://api.stripe.com/v1/charges``
    # hit the same cache key and the same DB row. Without this the same tool
    # under two case/slash variants would carry independent scores and twice
    # the LLM-bootstrap cost.
    body.tool_identifier = normalize_identifier(body.tool_identifier)

    ctx_hash = _context_hash(body.context)
    data_pool = effective_data_pool(api_key.data_pool)

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
        return await _cold_start(body, db, redis, ctx_hash, data_pool)

    # Lazy jurisdiction backfill — one-time cost per pre-existing tool.
    # Guard with a Redis "attempted" marker so a tool that consistently fails
    # enrichment (dead domain, blocked ipinfo, timeout) doesn't re-run the
    # full DNS+WHOIS+ipinfo.io pipeline on every request for an hour.
    if not tool.jurisdiction_category:
        enrich_mark_key = f"enrich_tried:{tool.id}"
        if not await redis.get(enrich_mark_key):
            from app.services.jurisdiction import enrich_tool
            try:
                enriched = await enrich_tool(tool)
            except Exception:
                logger.warning(
                    "Lazy jurisdiction backfill failed for %s", body.tool_identifier,
                    exc_info=True,
                )
                enriched = False
            # Either we succeeded (persist + refresh) or we failed (mark the
            # attempt so we don't thrash the network on the next request).
            if enriched:
                await db.commit()
                await db.refresh(tool)
            await redis.set(enrich_mark_key, "1", ex=3600)

    # Check cache. The cached score is invariant in eu_only/gdpr_required AND
    # in the budget-related request params, so we still use the cache on those
    # requests and augment with eu_alternatives + cost fields after the fact.
    # `eu_only` is the stricter filter (EU only) and must override
    # `gdpr_required` (EU + GDPR-adequate) when both are set.
    cached = await get_cached_score(redis, str(tool.id), ctx_hash, data_pool)
    if cached:
        if body.eu_only or body.gdpr_required:
            from app.services.scoring import _get_eu_alternatives
            cached.eu_alternatives = await _get_eu_alternatives(
                db, tool,
                gdpr_required=body.gdpr_required and not body.eu_only,
            )
        # Re-run cost augmentation with the CURRENT request's budget params.
        # The cached row never carries budget-specific values, so different
        # callers asking with different max_price_per_call / strategy each
        # get a correctly-weighted response.
        return await _finalize_with_body(cached, db, tool, body)

    # Compute score
    response = await compute_score(
        db, tool, ctx_hash, data_pool,
        eu_only=body.eu_only, gdpr_required=body.gdpr_required,
    )

    # Cache the flag-invariant version BEFORE applying cost augmentation, so
    # the cached entry carries no eu_alternatives and no budget-dependent
    # fields. Both are re-applied per request on cache hit via
    # _finalize_with_body above.
    cacheable = response.model_copy(update={"eu_alternatives": []})
    ttl = settings.cache_ttl_hot if tool.report_count >= settings.hot_threshold_reports_7d else settings.cache_ttl_cold
    await set_cached_score(redis, str(tool.id), ctx_hash, data_pool, cacheable, ttl)

    return await _finalize_with_body(response, db, tool, body)


@router.post("/assess/batch", tags=["Assessment"],
             summary="Batch assess multiple tools",
             description="Assess up to 20 tools in a single request. Each tool is scored independently "
                         "and counts as one assessment against your plan quota. "
                         "Useful for evaluating a full fallback chain upfront.")
async def batch_assess_tools(
    body: BatchAssessRequest,
    db: Db,
    redis: RedisClient,
    api_key: AuthenticatedKey,
):
    # Rate limiting: `get_api_key` already counted this request as 1 hit
    # against the period counter, but a batch holds up to 20 assessments.
    # Without this step, a user on a 100/day free tier could issue twenty
    # batches of 20 and get 2,000 assessments while only registering 20
    # rate-limit hits. Reserve the remaining (N-1) items atomically so the
    # quota matches the billable work — and so a rejected batch rolls back
    # cleanly instead of leaving the counter at limit+excess and locking
    # the user out for the rest of the period.
    from app.core.exceptions import RateLimitExceeded
    from app.services.rate_limiter import reserve_rate_limit
    period = api_key.billing_period or "daily"  # type: ignore[assignment]
    extra = len(body.tools) - 1
    if extra > 0:
        allowed, _count = await reserve_rate_limit(
            redis, api_key.key_hash, extra, api_key.daily_limit, period,
        )
        if not allowed:
            raise RateLimitExceeded()

    async def _assess_one(item: BatchAssessItem) -> dict:
        req = AssessRequest(tool_identifier=item.tool_identifier, context=item.context)
        try:
            result = await assess_tool(req, db, redis, api_key)
            return {"tool_identifier": item.tool_identifier, "result": result}
        except Exception as e:
            # Reset the shared session so a mid-batch DB error (transaction
            # aborted, integrity violation on tool upsert, etc.) doesn't
            # poison every subsequent item in the batch with
            # `current transaction is aborted`.
            try:
                await db.rollback()
            except Exception:
                pass
            return {"tool_identifier": item.tool_identifier, "error": str(e)}

    # Run assessments sequentially (they share the same DB session)
    results = []
    for item in body.tools:
        results.append(await _assess_one(item))

    return {"assessments": results, "count": len(results)}


async def _cold_start(body: AssessRequest, db: Db, redis: RedisClient, ctx_hash: str, data_pool: str | None):
    """Handle assessment for unknown tools — try LLM assessment, fall back to Bayesian prior."""
    from app.services.report_ingest import upsert_tool
    from app.services.scoring import _cold_start_response, compute_score
    from app.services.llm_assess import assess_tool_with_llm, create_tool_from_assessment
    from app.services.jurisdiction import enrich_tool
    from datetime import datetime, timezone

    tool = await upsert_tool(db, body.tool_identifier)
    # Enrich jurisdiction eagerly. Network failures (DNS/WHOIS/ipinfo.io) must
    # not leave the new Tool row uncommitted — the next request would then
    # re-insert it, and with a unique constraint on `identifier` we'd hit an
    # IntegrityError loop.
    try:
        await enrich_tool(tool)
    except Exception:
        logger.warning(
            "Jurisdiction enrichment failed for %s during cold start", body.tool_identifier,
            exc_info=True,
        )
    await db.commit()
    await redis.set(f"tool:{body.tool_identifier}", str(tool.id), ex=3600)

    # Try on-demand LLM assessment for an intelligent first response
    # Use a Redis lock to prevent concurrent LLM calls for the same tool
    if settings.anthropic_api_key:
        lock_key = f"llm_assess_lock:{body.tool_identifier}"
        acquired = await redis.set(lock_key, "1", ex=60, nx=True)
        if acquired:
            assessment = await assess_tool_with_llm(body.tool_identifier, context=body.context)
            if assessment:
                await create_tool_from_assessment(db, tool, assessment)
                response = await compute_score(
                    db, tool, ctx_hash, data_pool,
                    eu_only=body.eu_only, gdpr_required=body.gdpr_required,
                )
                # Cache the flag-invariant version BEFORE cost augmentation —
                # budget-specific fields are re-computed per request.
                cacheable = response.model_copy(update={"eu_alternatives": []})
                await set_cached_score(redis, str(tool.id), ctx_hash, data_pool, cacheable, settings.cache_ttl_cold)
                return await _finalize_with_body(response, db, tool, body)
        else:
            # Another request is already running LLM assessment — wait briefly and check cache
            await asyncio.sleep(2)
            cached = await get_cached_score(redis, str(tool.id), ctx_hash, data_pool)
            if cached:
                if body.eu_only or body.gdpr_required:
                    from app.services.scoring import _get_eu_alternatives
                    cached.eu_alternatives = await _get_eu_alternatives(
                        db, tool,
                        gdpr_required=body.gdpr_required and not body.eu_only,
                    )
                return await _finalize_with_body(cached, db, tool, body)

    # Tool has jurisdiction data from enrich_tool above; build the response from it.
    cold = _cold_start_response(datetime.now(timezone.utc), tool)
    if body.eu_only or body.gdpr_required:
        from app.services.scoring import _get_eu_alternatives
        cold.eu_alternatives = await _get_eu_alternatives(
            db, tool,
            gdpr_required=body.gdpr_required and not body.eu_only,
        )
    return await _finalize_with_body(cold, db, tool, body)
