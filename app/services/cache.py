import json
from datetime import datetime, timezone

from redis.asyncio import Redis

from app.schemas.assess import AssessResponse


def _cache_key(tool_id: str, context_hash: str, data_pool: str | None) -> str:
    return f"score:{tool_id}:{context_hash}:{data_pool or '__default__'}"


async def get_cached_score(
    redis: Redis, tool_id: str, context_hash: str, data_pool: str | None
) -> AssessResponse | None:
    key = _cache_key(tool_id, context_hash, data_pool)
    data = await redis.get(key)
    if data is None:
        return None
    try:
        return AssessResponse.model_validate_json(data)
    except Exception:
        # Corrupted cache entry — delete it and fall through to recompute
        await redis.delete(key)
        return None


async def set_cached_score(
    redis: Redis,
    tool_id: str,
    context_hash: str,
    data_pool: str | None,
    response: AssessResponse,
    ttl: int,
) -> None:
    key = _cache_key(tool_id, context_hash, data_pool)
    await redis.set(key, response.model_dump_json(), ex=ttl)
