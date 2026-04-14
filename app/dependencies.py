from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header, Request
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import InvalidApiKey, RateLimitExceeded
from app.core.security import hash_api_key
from app.db.session import async_session
from app.models.api_key import ApiKey
from app.services.rate_limiter import check_rate_limit, check_ip_rate_limit


async def get_db():
    async with async_session() as session:
        yield session


async def get_redis(request: Request) -> Redis:
    return request.app.state.redis


async def get_api_key(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    request: Request,
    # Optional at the Pydantic layer so a missing header returns a clean
    # 401 ("API key is required") instead of a generic 422 validation error.
    # A 422 tells the caller "your request body is malformed", which is the
    # wrong diagnosis for the common case of forgetting the X-Api-Key header.
    x_api_key: Annotated[str | None, Header()] = None,
) -> ApiKey:
    if not x_api_key:
        raise InvalidApiKey()

    # Per-IP burst protection runs BEFORE the DB lookup so a flood of
    # requests with bogus keys can't chew through the Postgres connection
    # pool — each bogus call was costing a full `SELECT FROM api_keys`.
    client_ip = request.client.host if request.client else "unknown"
    if not await check_ip_rate_limit(redis, client_ip):
        raise RateLimitExceeded()

    key_hash = hash_api_key(x_api_key)

    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)  # noqa: E712
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise InvalidApiKey()

    # Primary quota counter — period + hard limit depend on the tier
    period = api_key.billing_period or "daily"
    allowed, current_count = await check_rate_limit(
        redis, key_hash, api_key.daily_limit, period
    )
    if not allowed:
        raise RateLimitExceeded()

    # PAYG: ALSO read the daily counter to decide whether this call is "free"
    # or "metered overage". The primary counter above is the daily hard safety
    # cap; the free-grant check is orthogonal.
    request.state.is_payg_overage = False
    if api_key.tier == "payg":
        free_grant = settings.payg_free_daily_calls
        # current_count here is daily — PAYG uses billing_period=daily for the
        # safety cap, so we can reuse it.
        if current_count > free_grant:
            request.state.is_payg_overage = True

    # Rate limit headers — Pro shows the monthly window, others show daily.
    request.state.rate_limit = api_key.daily_limit
    request.state.rate_remaining = max(0, api_key.daily_limit - current_count)
    request.state.rate_period = period

    # Touch last_used_at at most once every 5 minutes per key. The Redis mark
    # acts as a per-key throttle so we don't turn every request into a DB
    # write — the dashboard only needs ~minute-level freshness for this field.
    mark_key = f"lastused_mark:{key_hash}"
    if await redis.set(mark_key, "1", ex=300, nx=True):
        now_utc = datetime.now(timezone.utc)
        await db.execute(
            update(ApiKey).where(ApiKey.id == api_key.id).values(last_used_at=now_utc)
        )
        await db.commit()
        # Mirror the write on the already-loaded ORM instance so downstream
        # handlers (e.g. /v1/me/dashboard) see the fresh value without an
        # extra round-trip.
        api_key.last_used_at = now_utc

    return api_key


async def require_admin_key(api_key: Annotated[ApiKey, Depends(get_api_key)]) -> ApiKey:
    """Reject with 403 unless the caller is using an admin-tier key."""
    if api_key.tier != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required")
    return api_key


Db = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]
AuthenticatedKey = Annotated[ApiKey, Depends(get_api_key)]
AdminKey = Annotated[ApiKey, Depends(require_admin_key)]
