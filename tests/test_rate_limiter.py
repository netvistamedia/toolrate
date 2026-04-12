"""Tests for the Redis-backed rate limiter.

Focus: the atomic INCR+EXPIRE Lua script must always leave a TTL on the key,
even under concurrent increments, so stale counters never accumulate.
"""
import asyncio

import fakeredis.aioredis
import pytest
import pytest_asyncio

from app.services.rate_limiter import (
    check_ip_rate_limit,
    check_rate_limit,
    _incr_with_ttl,
)
from app.config import settings


@pytest_asyncio.fixture
async def redis():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


class TestIncrWithTTL:
    @pytest.mark.asyncio
    async def test_sets_ttl_on_first_hit(self, redis):
        count = await _incr_with_ttl(redis, "test:key", 60)
        assert count == 1
        ttl = await redis.ttl("test:key")
        assert 0 < ttl <= 60

    @pytest.mark.asyncio
    async def test_subsequent_hits_keep_ttl(self, redis):
        await _incr_with_ttl(redis, "test:key", 60)
        first_ttl = await redis.ttl("test:key")
        await _incr_with_ttl(redis, "test:key", 60)
        second_ttl = await redis.ttl("test:key")
        # TTL should not be reset on subsequent hits
        assert second_ttl <= first_ttl
        assert second_ttl > 0

    @pytest.mark.asyncio
    async def test_counter_increments(self, redis):
        counts = []
        for _ in range(5):
            counts.append(await _incr_with_ttl(redis, "test:key", 60))
        assert counts == [1, 2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_concurrent_increments_all_have_ttl(self, redis):
        """Even with many concurrent increments, the key must end with a valid TTL."""
        async def hit():
            return await _incr_with_ttl(redis, "burst:key", 60)

        results = await asyncio.gather(*[hit() for _ in range(50)])
        # All 50 increments should succeed
        assert sorted(results) == list(range(1, 51))
        # And the key must have a TTL, not be stuck at -1 (no expiry)
        ttl = await redis.ttl("burst:key")
        assert ttl > 0, "Lua script failed to set TTL under concurrent load"


class TestCheckRateLimit:
    @pytest.mark.asyncio
    async def test_allows_up_to_limit(self, redis):
        for i in range(1, 6):
            allowed, count = await check_rate_limit(redis, "hash-abc", limit=5)
            assert allowed is True
            assert count == i

    @pytest.mark.asyncio
    async def test_blocks_over_limit(self, redis):
        for _ in range(5):
            await check_rate_limit(redis, "hash-abc", limit=5)
        allowed, count = await check_rate_limit(redis, "hash-abc", limit=5)
        assert allowed is False
        assert count == 6

    @pytest.mark.asyncio
    async def test_separate_keys_have_separate_counters(self, redis):
        await check_rate_limit(redis, "hash-a", limit=10)
        await check_rate_limit(redis, "hash-a", limit=10)
        _, count_b = await check_rate_limit(redis, "hash-b", limit=10)
        assert count_b == 1

    @pytest.mark.asyncio
    async def test_key_has_day_scoped_ttl(self, redis):
        await check_rate_limit(redis, "hash-abc", limit=5)
        # There should be exactly one rate-limit key with a TTL around 25h
        keys = await redis.keys("rl:hash-abc:*")
        assert len(keys) == 1
        ttl = await redis.ttl(keys[0])
        assert 0 < ttl <= 90000


class TestCheckIpRateLimit:
    @pytest.mark.asyncio
    async def test_allows_within_limit(self, redis):
        allowed = await check_ip_rate_limit(redis, "1.2.3.4")
        assert allowed is True

    @pytest.mark.asyncio
    async def test_blocks_over_limit(self, redis):
        # Hit the configured cap
        for _ in range(settings.per_ip_per_minute):
            assert await check_ip_rate_limit(redis, "1.2.3.4") is True
        # Next call should be blocked
        assert await check_ip_rate_limit(redis, "1.2.3.4") is False

    @pytest.mark.asyncio
    async def test_uses_configured_per_minute_limit(self, redis, monkeypatch):
        """The limiter should honor settings.per_ip_per_minute, not a hardcoded 60."""
        monkeypatch.setattr(settings, "per_ip_per_minute", 3)
        assert await check_ip_rate_limit(redis, "5.6.7.8") is True
        assert await check_ip_rate_limit(redis, "5.6.7.8") is True
        assert await check_ip_rate_limit(redis, "5.6.7.8") is True
        assert await check_ip_rate_limit(redis, "5.6.7.8") is False
