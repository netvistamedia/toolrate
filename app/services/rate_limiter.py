from datetime import datetime, timezone

from redis.asyncio import Redis


async def check_rate_limit(redis: Redis, key_hash: str, daily_limit: int) -> tuple[bool, int]:
    """Check if the API key has exceeded its daily limit.
    Returns (allowed, current_count)."""
    date_key = f"rl:{key_hash}:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    count = await redis.incr(date_key)
    if count == 1:
        await redis.expire(date_key, 90000)  # 25 hours
    return count <= daily_limit, count


async def check_ip_rate_limit(redis: Redis, client_ip: str) -> bool:
    """Check per-IP burst limit (60 req/min)."""
    ip_key = f"rl:ip:{client_ip}"
    count = await redis.incr(ip_key)
    if count == 1:
        await redis.expire(ip_key, 60)
    return count <= 60
