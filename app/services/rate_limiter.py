from datetime import datetime, timezone

from redis.asyncio import Redis

from app.config import settings

# Atomic INCR + EXPIRE-on-first-hit. Using EVAL means Redis runs both commands
# in a single server-side step, so we can't lose the TTL if the client dies
# between calls — which was the hazard with the previous two-command version.
_INCR_WITH_TTL_LUA = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


async def _incr_with_ttl(redis: Redis, key: str, ttl_seconds: int) -> int:
    return await redis.eval(_INCR_WITH_TTL_LUA, 1, key, ttl_seconds)


async def check_rate_limit(redis: Redis, key_hash: str, daily_limit: int) -> tuple[bool, int]:
    """Check if the API key has exceeded its daily limit.
    Returns (allowed, current_count)."""
    date_key = f"rl:{key_hash}:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    count = await _incr_with_ttl(redis, date_key, 90000)  # 25 hours
    return count <= daily_limit, count


async def check_ip_rate_limit(redis: Redis, client_ip: str) -> bool:
    """Check per-IP burst limit."""
    ip_key = f"rl:ip:{client_ip}"
    count = await _incr_with_ttl(redis, ip_key, 60)
    return count <= settings.per_ip_per_minute
