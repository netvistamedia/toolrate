"""Tests for the admin dashboard endpoint and HTML page."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.security import generate_api_key, make_fingerprint
from app.dependencies import get_db
from app.main import app
from app.models.api_key import ApiKey
from app.models.report import ExecutionReport
from app.models.tool import Tool


@pytest_asyncio.fixture
async def client_and_db(db_engine, monkeypatch):
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    # Replace the real Redis with fakeredis for this client
    import fakeredis.aioredis
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)

    class _FakeState:
        pass

    app.state.redis = fake
    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, session_factory, fake
    finally:
        app.dependency_overrides.pop(get_db, None)
        await fake.aclose()


async def _make_key(session_factory, tier: str) -> str:
    full, key_hash, prefix = generate_api_key()
    async with session_factory() as db:
        db.add(ApiKey(
            key_hash=key_hash,
            key_prefix=prefix,
            tier=tier,
            daily_limit=100_000,
            billing_period="daily",
            is_active=True,
        ))
        await db.commit()
    return full


@pytest.mark.asyncio
async def test_dashboard_rejects_non_admin(client_and_db):
    ac, sf, _ = client_and_db
    free_key = await _make_key(sf, "free")
    r = await ac.get("/v1/admin/dashboard", headers={"X-Api-Key": free_key})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_dashboard_rejects_missing_key(client_and_db):
    ac, _, _ = client_and_db
    r = await ac.get("/v1/admin/dashboard")
    assert r.status_code == 422  # missing header


@pytest.mark.asyncio
async def test_dashboard_returns_expected_shape(client_and_db):
    ac, sf, _ = client_and_db
    admin_key = await _make_key(sf, "admin")

    # Seed a tool + a few reports (today + yesterday)
    now = datetime.now(timezone.utc)
    async with sf() as db:
        tool = Tool(
            id=uuid.uuid4(),
            identifier="https://api.example.com/v1/thing",
            display_name="Example API",
            category="test",
            report_count=5,
        )
        db.add(tool)
        await db.flush()

        for i in range(4):  # 4 success
            db.add(ExecutionReport(
                tool_id=tool.id, success=True, latency_ms=100,
                context_hash="__global__", reporter_fingerprint="fp-a",
                created_at=now - timedelta(minutes=i * 5),
            ))
        db.add(ExecutionReport(  # 1 failure
            tool_id=tool.id, success=False, error_category="timeout",
            latency_ms=2000, context_hash="__global__",
            reporter_fingerprint="fp-b",
            created_at=now - timedelta(minutes=10),
        ))

        # ── Synthetic reports that MUST be excluded from real counters ──
        synth_fp = make_fingerprint("llm_ondemand", "llm_ondemand")
        for _ in range(50):
            db.add(ExecutionReport(
                tool_id=tool.id, success=True, latency_ms=120,
                context_hash="__global__", reporter_fingerprint=synth_fp,
                created_at=now - timedelta(minutes=30),
            ))
        await db.commit()

    r = await ac.get("/v1/admin/dashboard", headers={"X-Api-Key": admin_key})
    assert r.status_code == 200, r.text
    data = r.json()

    # Shape
    for section in ("today", "trend", "reliability", "top_tools",
                    "errors_today", "totals", "billing"):
        assert section in data, f"missing section {section}"

    # Today tiles match the seeded REAL data (synthetic 50 excluded)
    assert data["today"]["reports_total"] == 5
    assert data["today"]["reports_successful"] == 4
    assert data["today"]["reports_failed"] == 1
    assert data["today"]["success_rate_pct"] == 80.0
    assert data["today"]["unique_reporters"] == 2  # fp-a + fp-b
    assert data["today"]["tools_touched"] == 1
    assert data["today"]["synthetic_bootstrap_reports"] == 50

    # Trend buckets populated
    assert len(data["trend"]["hourly_24h"]) >= 1
    assert len(data["trend"]["daily_30d"]) >= 1

    # Top tools
    busiest = data["top_tools"]["busiest_24h"]
    assert len(busiest) == 1
    assert busiest[0]["reports_24h"] == 5
    assert abs(busiest[0]["success_rate"] - 0.8) < 0.001

    # Error category counted
    errors = {e["category"]: e["count"] for e in data["errors_today"]}
    assert errors.get("timeout") == 1

    # Totals include the admin key itself
    assert data["totals"]["active_keys"] >= 1
    assert "admin" in data["totals"]["by_tier"]


@pytest.mark.asyncio
async def test_dashboard_page_renders():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/dashboard")
    assert r.status_code == 200
    body = r.text
    assert "Admin Dashboard" in body
    assert "/v1/admin/dashboard" in body  # fetch target wired
    assert "nemoflow_admin_key" in body   # localStorage key
