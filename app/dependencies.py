from typing import Annotated

from fastapi import Depends, Header, Request
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    x_api_key: Annotated[str, Header()],
) -> ApiKey:
    key_hash = hash_api_key(x_api_key)

    # Check API key
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)  # noqa: E712
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise InvalidApiKey()

    # Check IP rate limit
    client_ip = request.client.host if request.client else "unknown"
    if not await check_ip_rate_limit(redis, client_ip):
        raise RateLimitExceeded()

    # Check daily rate limit
    allowed, current_count = await check_rate_limit(redis, key_hash, api_key.daily_limit)
    if not allowed:
        raise RateLimitExceeded()

    # Store rate limit info for response headers
    request.state.rate_limit = api_key.daily_limit
    request.state.rate_remaining = max(0, api_key.daily_limit - current_count)

    return api_key


Db = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]
AuthenticatedKey = Annotated[ApiKey, Depends(get_api_key)]
