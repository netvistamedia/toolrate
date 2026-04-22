"""Tests for POST /v1/auth/register guards.

Guard against self-domain registrations — verification curls using
`something@toolrate.ai` used to land in prod, create synthetic API keys,
pollute the `source` attribution stats, and fire a welcome email that
looped through our own SendGrid inbound parse.
"""

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.dependencies import get_db
from app.main import app
from app.models.api_key import ApiKey


@pytest_asyncio.fixture
async def client(db_engine, monkeypatch):
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app.state.redis = fake_redis
    app.dependency_overrides[get_db] = override_get_db

    # Silence the welcome-email path — the real send would try to talk to
    # SendGrid. Tests that verify the guard shouldn't reach this anyway,
    # but the happy-path test needs it stubbed.
    from app.services import email as email_service

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(email_service, "send_welcome_email", _noop)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, session_factory
    finally:
        app.dependency_overrides.pop(get_db, None)
        await fake_redis.aclose()


@pytest.mark.asyncio
async def test_rejects_self_domain_registration(client):
    ac, session_factory = client
    resp = await ac.post(
        "/v1/auth/register",
        json={"email": "verify-source-track-1776694538@toolrate.ai", "source": "mcp"},
    )
    assert resp.status_code == 400
    assert "toolrate" in resp.json()["detail"].lower()

    # No row should have been created.
    async with session_factory() as db:
        rows = (await db.execute(select(ApiKey))).scalars().all()
        assert rows == []


@pytest.mark.asyncio
async def test_rejects_self_domain_uppercase(client):
    ac, _ = client
    resp = await ac.post(
        "/v1/auth/register",
        json={"email": "anything@ToolRate.AI"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_accepts_external_email(client):
    ac, session_factory = client
    resp = await ac.post(
        "/v1/auth/register",
        json={"email": "dev@example.com", "source": "mcp"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "free"
    assert body["api_key"].startswith("nf_live_")

    async with session_factory() as db:
        rows = (await db.execute(select(ApiKey))).scalars().all()
        assert len(rows) == 1
        assert rows[0].source == "mcp"
