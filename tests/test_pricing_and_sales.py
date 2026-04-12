"""Tests for the /pricing page, contact-sales endpoint, PAYG metering, and
the daily/monthly rate limiter branching.
"""

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.dependencies import get_db
from app.models.api_key import ApiKey
from app.models.audit_log import AuditLog
from app.services.rate_limiter import check_rate_limit, current_usage
from app.services.payg_meter import record_assessment


# ───────────────────────────────────────────────────────────────────────────
# Pricing page
# ───────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pricing_page_renders_in_usd():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/pricing")
    assert r.status_code == 200
    body = r.text
    # All four plans present
    assert "Free" in body
    assert "Pay-as-you-go" in body
    assert "Best for agents" in body  # featured badge
    assert "$0.008" in body
    assert "$29" in body
    assert "Enterprise" in body
    # No Euro leftovers
    assert "€" not in body
    assert "EUR" not in body
    assert '"priceCurrency": "USD"' in body


@pytest.mark.asyncio
async def test_landing_pricing_uses_usd_and_payg():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/")
    assert r.status_code == 200
    body = r.text
    assert "$0.008" in body
    assert "$29" in body
    assert "Pay-as-you-go" in body
    assert "€" not in body


@pytest.mark.asyncio
async def test_upgrade_page_defaults_to_payg():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/upgrade")
        assert r.status_code == 200
        assert "Pay-as-you-go" in r.text or "PAYG" in r.text
        assert "$0.008" in r.text

        r2 = await ac.get("/upgrade?plan=pro")
        assert r2.status_code == 200
        assert "$29" in r2.text
        assert "10,000 assessments" in r2.text


# ───────────────────────────────────────────────────────────────────────────
# Contact-sales endpoint
# ───────────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client_with_db(db_engine):
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, session_factory
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_contact_sales_persists_audit_row(client_with_db):
    ac, session_factory = client_with_db
    payload = {
        "company": "Acme AI",
        "name": "Jane Doe",
        "email": "jane@acme.ai",
        "volume": "10M",
        "use_case": "We're building an AI coding platform with 50k active devs.",
    }
    r = await ac.post("/v1/billing/contact-sales", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"

    async with session_factory() as s:
        rows = (await s.execute(
            select(AuditLog).where(AuditLog.action == "enterprise_lead_submitted")
        )).scalars().all()
    assert len(rows) == 1
    assert rows[0].detail["company"] == "Acme AI"


@pytest.mark.asyncio
async def test_contact_sales_rejects_malformed(client_with_db):
    ac, _ = client_with_db
    r = await ac.post("/v1/billing/contact-sales", json={
        "company": "",
        "email": "not-an-email",
        "volume": "",
        "use_case": "short",
    })
    assert r.status_code == 422


# ───────────────────────────────────────────────────────────────────────────
# Rate limiter — daily vs monthly
# ───────────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def redis():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


@pytest.mark.asyncio
async def test_daily_and_monthly_buckets_are_independent(redis):
    """A daily increment must not affect the monthly counter and vice versa."""
    for _ in range(5):
        await check_rate_limit(redis, "k1", limit=1000, period="daily")
    for _ in range(3):
        await check_rate_limit(redis, "k1", limit=1000, period="monthly")
    assert await current_usage(redis, "k1", "daily") == 5
    assert await current_usage(redis, "k1", "monthly") == 3


@pytest.mark.asyncio
async def test_monthly_limit_blocks_when_exceeded(redis):
    for i in range(1, 4):
        allowed, count = await check_rate_limit(redis, "pro-key", limit=3, period="monthly")
        assert allowed is True
        assert count == i
    allowed, count = await check_rate_limit(redis, "pro-key", limit=3, period="monthly")
    assert allowed is False
    assert count == 4


# ───────────────────────────────────────────────────────────────────────────
# PAYG metering
# ───────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_payg_meter_is_free_under_grant(redis, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "payg_free_daily_calls", 10)

    key = ApiKey(
        key_hash="payg-hash",
        key_prefix="nf_test",
        tier="payg",
        daily_limit=100000,
        billing_period="daily",
    )

    for i in range(1, 11):
        info = await record_assessment(redis, key)
        assert info["assess_today"] == i
        assert info["billable"] is False


@pytest.mark.asyncio
async def test_payg_meter_marks_overage_billable(redis, monkeypatch):
    from app.config import settings
    # Disable Stripe completely so the fire-and-forget meter call is a no-op.
    monkeypatch.setattr(settings, "stripe_secret_key", "")
    monkeypatch.setattr(settings, "stripe_payg_price_id", "")
    monkeypatch.setattr(settings, "payg_free_daily_calls", 2)

    key = ApiKey(
        key_hash="payg-hash-2",
        key_prefix="nf_test",
        tier="payg",
        daily_limit=100000,
        billing_period="daily",
    )

    # First 2 are free
    for _ in range(2):
        info = await record_assessment(redis, key)
        assert info["billable"] is False

    # 3rd and beyond are billable
    info = await record_assessment(redis, key)
    assert info["billable"] is True
    assert info["assess_today"] == 3


@pytest.mark.asyncio
async def test_free_tier_never_billable(redis):
    key = ApiKey(
        key_hash="free-hash",
        key_prefix="nf_test",
        tier="free",
        daily_limit=100,
        billing_period="daily",
    )
    for _ in range(5):
        info = await record_assessment(redis, key)
        assert info["billable"] is False
