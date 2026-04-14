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

# Atomic INCRBY + EXPIRE + overflow rollback. Reserves N quota units in one
# step: if the increment would push the counter over `limit`, we DECRBY back
# to the pre-call value and return -1 so the caller sees "no reservation made".
# This is what batch_assess_tools needs — the naive loop-INCR pattern would
# leave the counter at limit+excess on a rejected batch and lock the user out
# for the rest of the period.
_RESERVE_LUA = """
local n = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])
local count = redis.call('INCRBY', KEYS[1], n)
if count == n then
    redis.call('EXPIRE', KEYS[1], ttl)
end
if count > limit then
    redis.call('DECRBY', KEYS[1], n)
    return -1
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


async def reserve_rate_limit(
    redis: Redis,
    key_hash: str,
    n: int,
    limit: int,
    period: Period = "daily",
) -> tuple[bool, int]:
    """Atomically reserve N quota units in one round trip.

    Returns (allowed, count_after). If the reservation would exceed ``limit``,
    the counter is rolled back to its pre-call value and ``allowed`` is False —
    no partial reservation ever sticks. ``count_after`` is the pre-call count
    on rejection and the post-call count on success, so callers can still
    surface an accurate X-RateLimit-Remaining header either way.
    """
    if n <= 0:
        current = await current_usage(redis, key_hash, period)
        return True, current
    rkey, ttl = _period_key(key_hash, period)
    result = await redis.eval(_RESERVE_LUA, 1, rkey, n, limit, ttl)
    result = int(result)
    if result == -1:
        current = await current_usage(redis, key_hash, period)
        return False, current
    return True, result


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
