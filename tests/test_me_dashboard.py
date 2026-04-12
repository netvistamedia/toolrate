"""Tests for the customer-facing /v1/me/dashboard endpoint and /me HTML page."""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.security import generate_api_key
from app.dependencies import get_db
from app.main import app
from app.models.api_key import ApiKey


@pytest_asyncio.fixture
async def client_and_db(db_engine):
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    import fakeredis.aioredis
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)

    app.state.redis = fake
    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, session_factory, fake
    finally:
        app.dependency_overrides.pop(get_db, None)
        await fake.aclose()


async def _make_key(
    session_factory,
    *,
    tier: str = "free",
    daily_limit: int = 100,
    billing_period: str = "daily",
) -> tuple[str, str]:
    """Create an ApiKey and return (full_key, key_hash)."""
    full, key_hash, prefix = generate_api_key()
    async with session_factory() as db:
        db.add(ApiKey(
            key_hash=key_hash,
            key_prefix=prefix,
            tier=tier,
            daily_limit=daily_limit,
            billing_period=billing_period,
            is_active=True,
        ))
        await db.commit()
    return full, key_hash


@pytest.mark.asyncio
async def test_rejects_missing_key(client_and_db):
    ac, _, _ = client_and_db
    r = await ac.get("/v1/me/dashboard")
    assert r.status_code == 422  # missing X-Api-Key header


@pytest.mark.asyncio
async def test_rejects_invalid_key(client_and_db):
    ac, _, _ = client_and_db
    r = await ac.get("/v1/me/dashboard", headers={"X-Api-Key": "nf_live_nope"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_free_tier_shape_and_empty_history(client_and_db):
    ac, sf, _ = client_and_db
    key, _ = await _make_key(sf, tier="free", daily_limit=100)

    r = await ac.get("/v1/me/dashboard", headers={"X-Api-Key": key})
    assert r.status_code == 200, r.text
    data = r.json()

    # Shape
    for section in ("account", "current_period", "usage_last_30d",
                    "usage_totals", "billing", "status", "upgrade"):
        assert section in data, f"missing section {section}"

    assert data["account"]["tier"] == "free"
    assert data["account"]["billing_period"] == "daily"
    assert data["current_period"]["label"] == "Today"
    assert data["current_period"]["limit"] == 100
    # The auth path increments the daily counter by 1
    assert data["current_period"]["used"] == 1
    assert data["current_period"]["remaining"] == 99
    assert data["current_period"]["percent_used"] == 1.0

    # 30-day history is zero-filled for every day
    assert len(data["usage_last_30d"]) == 30
    assert all(r["count"] == 0 for r in data["usage_last_30d"])
    assert data["usage_totals"]["total_30d"] == 0
    assert data["usage_totals"]["peak_day"] is None

    assert data["billing"]["plan"] == "free"
    assert data["billing"]["free_daily_calls"] == 100
    assert data["status"]["health"] == "ok"
    assert data["upgrade"]["suggested_plan"] is None


@pytest.mark.asyncio
async def test_usage_history_reads_assess_counters(client_and_db):
    """Seeding `assess:{hash}:{date}` keys in Redis should show up in the
    30-day sparkline with correct totals and peak."""
    ac, sf, fake = client_and_db
    key, key_hash = await _make_key(sf, tier="payg", daily_limit=100000)

    today = datetime.now(timezone.utc).date()
    # Seed 3 days of history: today = 50, yesterday = 120 (peak), 2 days ago = 30
    await fake.set(f"assess:{key_hash}:{today.isoformat()}", "50")
    await fake.set(
        f"assess:{key_hash}:{(today - timedelta(days=1)).isoformat()}", "120"
    )
    await fake.set(
        f"assess:{key_hash}:{(today - timedelta(days=2)).isoformat()}", "30"
    )

    r = await ac.get("/v1/me/dashboard", headers={"X-Api-Key": key})
    assert r.status_code == 200, r.text
    data = r.json()

    hist = {row["date"]: row["count"] for row in data["usage_last_30d"]}
    assert hist[today.isoformat()] == 50
    assert hist[(today - timedelta(days=1)).isoformat()] == 120
    assert hist[(today - timedelta(days=2)).isoformat()] == 30

    assert data["usage_totals"]["total_30d"] == 200
    assert data["usage_totals"]["days_active_30d"] == 3
    # daily_avg = 200/30 = 6.67
    assert data["usage_totals"]["daily_avg"] == round(200 / 30.0, 2)
    assert data["usage_totals"]["peak_day"]["count"] == 120
    assert data["usage_totals"]["peak_day"]["date"] == (today - timedelta(days=1)).isoformat()


@pytest.mark.asyncio
async def test_payg_billing_snapshot(client_and_db):
    """PAYG keys should surface monthly billable count and estimated cost."""
    ac, sf, fake = client_and_db
    key, key_hash = await _make_key(sf, tier="payg", daily_limit=100000)

    month_tag = datetime.now(timezone.utc).strftime("%Y-%m")
    await fake.set(f"payg_billable:{key_hash}:{month_tag}", "250")

    r = await ac.get("/v1/me/dashboard", headers={"X-Api-Key": key})
    assert r.status_code == 200, r.text
    b = r.json()["billing"]

    assert b["plan"] == "payg"
    assert b["payg_billable_mtd"] == 250
    assert b["payg_free_daily_calls"] == 100
    # 250 × $0.008 = $2.00 (within rounding)
    assert abs(b["payg_estimated_cost_usd"] - 2.00) < 0.001
    assert abs(b["payg_price_per_call_usd"] - 0.008) < 1e-6


@pytest.mark.asyncio
async def test_pro_tier_uses_monthly_label(client_and_db):
    ac, sf, _ = client_and_db
    key, _ = await _make_key(sf, tier="pro", daily_limit=10000, billing_period="monthly")

    r = await ac.get("/v1/me/dashboard", headers={"X-Api-Key": key})
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["account"]["billing_period"] == "monthly"
    assert data["current_period"]["label"] == "Month-to-date"
    assert data["current_period"]["period"] == "monthly"
    assert data["billing"]["plan"] == "pro"
    assert data["billing"]["pro_monthly_included"] == 10000
    # resets_at should be first of next month at 00:00 UTC
    resets = datetime.fromisoformat(data["current_period"]["resets_at"])
    assert resets.day == 1
    assert resets.hour == 0 and resets.minute == 0


@pytest.mark.asyncio
async def test_near_limit_health_and_free_to_payg_upgrade_hint(client_and_db):
    """Free tier at ≥80% usage should flip health to near_limit and suggest PAYG."""
    ac, sf, fake = client_and_db
    key, key_hash = await _make_key(sf, tier="free", daily_limit=100)

    # Pre-load today's counter to 90 so we cross the 80% threshold on next hit
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await fake.set(f"rl:{key_hash}:{today}", "90")

    r = await ac.get("/v1/me/dashboard", headers={"X-Api-Key": key})
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["current_period"]["used"] == 91  # 90 + 1 from auth
    assert data["status"]["health"] == "near_limit"
    assert data["upgrade"]["suggested_plan"] == "payg"
    assert "Pay-as-you-go" in data["upgrade"]["reason"]


@pytest.mark.asyncio
async def test_payg_heavy_volume_suggests_pro(client_and_db):
    ac, sf, fake = client_and_db
    key, key_hash = await _make_key(sf, tier="payg", daily_limit=100000)

    month_tag = datetime.now(timezone.utc).strftime("%Y-%m")
    await fake.set(f"payg_billable:{key_hash}:{month_tag}", "1500")

    r = await ac.get("/v1/me/dashboard", headers={"X-Api-Key": key})
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["upgrade"]["suggested_plan"] == "pro"
    assert "Pro" in data["upgrade"]["reason"]


@pytest.mark.asyncio
async def test_me_page_renders():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/me")
    assert r.status_code == 200
    body = r.text
    assert "Your ToolRate account" in body
    assert "/v1/me/dashboard" in body  # fetch target wired
    assert "nemoflow_user_key" in body   # localStorage key
