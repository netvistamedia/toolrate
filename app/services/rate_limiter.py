from datetime import datetime, timezone
from typing import Literal

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

Period = Literal["daily", "monthly"]


async def _incr_with_ttl(redis: Redis, key: str, ttl_seconds: int) -> int:
    return await redis.eval(_INCR_WITH_TTL_LUA, 1, key, ttl_seconds)


def _period_key(key_hash: str, period: Period) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    if period == "monthly":
        return (
            f"rl:{key_hash}:m:{now.strftime('%Y-%m')}",
            40 * 24 * 3600,  # ~40 days
        )
    return (
        f"rl:{key_hash}:{now.strftime('%Y-%m-%d')}",
        90000,  # 25 hours
    )


async def check_rate_limit(
    redis: Redis,
    key_hash: str,
    limit: int,
    period: Period = "daily",
) -> tuple[bool, int]:
    """Check if the API key has exceeded its quota for the period.
    Returns (allowed, current_count)."""
    rkey, ttl = _period_key(key_hash, period)
    count = await _incr_with_ttl(redis, rkey, ttl)
    return count <= limit, count


async def check_ip_rate_limit(redis: Redis, client_ip: str) -> bool:
    """Check per-IP burst limit."""
    ip_key = f"rl:ip:{client_ip}"
    count = await _incr_with_ttl(redis, ip_key, 60)
    return count <= settings.per_ip_per_minute


async def current_usage(redis: Redis, key_hash: str, period: Period = "daily") -> int:
    """Read (without incrementing) the current period usage. Returns 0 if unset."""
    rkey, _ = _period_key(key_hash, period)
    val = await redis.get(rkey)
    return int(val) if val else 0
