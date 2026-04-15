"""Tests for app.main.validation_error_handler.

Before this fix a Pydantic v2 ``field_validator`` that raised ``ValueError``
turned into a 500 Internal Server Error because ``exc.errors()`` carries
the original exception object in the ``ctx`` dict, and Starlette's
``JSONResponse`` serialises straight through ``json.dumps`` which can't
handle ``ValueError`` objects. The fix routes the payload through
``fastapi.encoders.jsonable_encoder`` so any non-JSON Python object
becomes a string before Starlette sees it.

Two tests:

1. **Handler-only** — spins up a minimal FastAPI app with the real
   ``validation_error_handler`` from ``app.main`` attached. A dummy
   endpoint's ``field_validator`` raises ``ValueError`` and the test
   asserts the response is a clean 422 JSON body. No DB, no Redis,
   no API key — fast and focused on the handler logic itself.

2. **End-to-end** — hits the real ``POST /v1/webhooks`` with an RFC1918
   URL. This was the path that failed in production during the
   post-deploy smoke test on 2026-04-15. An authenticated request with
   a fake API key + fakeredis confirms the live endpoint now rejects
   private URLs with a proper 422 instead of a 500.
"""
from __future__ import annotations

import fakeredis.aioredis
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.security import generate_api_key
from app.dependencies import get_db
from app.main import app, validation_error_handler
from app.models.api_key import ApiKey


# ──────────────────────────────────────────────────────────────────────────
# Test 1 — handler-only, no infra
# ──────────────────────────────────────────────────────────────────────────
#
# Helper Pydantic models live at module scope on purpose: FastAPI's route
# signature introspection resolves type annotations at registration time,
# and Pydantic models defined inside the test body get resolved via the
# function's `__closure__` in ways FastAPI's `analyze_param` sometimes
# misreads as "this is a query parameter", leading to confusing
# "Field required, loc=['query', 'body']" errors that have nothing to do
# with the handler under test.


class _PositiveIntBody(BaseModel):
    x: int

    @field_validator("x")
    @classmethod
    def reject_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("must be positive")
        return v


class _MultiFieldBody(BaseModel):
    a: int
    b: str

    @field_validator("b")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("b must not be empty")
        return v


def _mini_app() -> FastAPI:
    """Build a throwaway FastAPI app wired to the real handler under test."""
    mini = FastAPI()
    mini.add_exception_handler(RequestValidationError, validation_error_handler)

    @mini.post("/positive")
    async def echo_positive(body: _PositiveIntBody):
        return {"ok": body.x}

    @mini.post("/multi")
    async def echo_multi(body: _MultiFieldBody):
        return {"ok": True}

    return mini


@pytest.mark.asyncio
async def test_handler_jsonifies_valueerror_ctx():
    """A Pydantic field_validator raising ValueError must produce a clean
    422 response. The old handler 500'd because ``exc.errors()`` returns
    a dict tree with the ValueError object in ``ctx``, and json.dumps
    raised TypeError on serialization.
    """
    transport = ASGITransport(app=_mini_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/positive", json={"x": -1})

    assert resp.status_code == 422
    payload = resp.json()
    assert payload["detail"] == "Validation error"
    assert isinstance(payload["errors"], list)
    assert len(payload["errors"]) >= 1
    # The validator message should survive the jsonable_encoder pass —
    # Pydantic v2 formats it as "Value error, <msg>" inside each entry's
    # `msg` field, so we confirm the substring appears somewhere in the
    # serialized response body.
    import json as _json
    assert "must be positive" in _json.dumps(payload)


@pytest.mark.asyncio
async def test_handler_preserves_multiple_errors():
    """Both missing-required-field errors AND custom ValueError errors
    should come through in a single 422 response. Regression guard for
    a hypothetical future short-circuit in the handler."""
    transport = ASGITransport(app=_mini_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Missing `a` AND empty `b` — two distinct validation errors
        resp = await ac.post("/multi", json={"b": ""})

    assert resp.status_code == 422
    errors = resp.json()["errors"]
    # Either the missing-field or the custom ValueError path is enough —
    # the old handler would 500 before reaching this assertion on the
    # ValueError path.
    assert len(errors) >= 1


# ──────────────────────────────────────────────────────────────────────────
# Test 2 — end-to-end against real POST /v1/webhooks
# ──────────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def authed_client(db_engine):
    """Real app client with in-memory DB + fakeredis + a valid API key.

    Mirrors the pattern from tests/test_billing_webhook.py::billing_client
    but narrower: no Stripe monkeypatching needed. Returns
    ``(client, api_key_header_value)`` so the test can send authed
    requests without re-deriving the key.
    """
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    full_key, key_hash, key_prefix = generate_api_key()
    async with session_factory() as db:
        db.add(
            ApiKey(
                key_hash=key_hash,
                key_prefix=key_prefix,
                tier="pro",
                daily_limit=10000,
                billing_period="daily",
            )
        )
        await db.commit()

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app.state.redis = fake_redis
    app.dependency_overrides[get_db] = override_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, full_key
    finally:
        app.dependency_overrides.pop(get_db, None)
        await fake_redis.aclose()


@pytest.mark.asyncio
async def test_webhooks_internal_ip_returns_422_not_500(authed_client):
    """This was the prod-500 scenario on 2026-04-15: registering a
    webhook URL pointing at an RFC1918 address triggered the field
    validator's ValueError, which the old handler couldn't serialize.
    The response now must be a clean 422."""
    client, api_key = authed_client

    resp = await client.post(
        "/v1/webhooks",
        headers={"X-Api-Key": api_key},
        json={
            "url": "http://10.0.0.5/hook",
            "event": "score.change",
            "threshold": 5,
        },
    )

    assert resp.status_code == 422, (
        f"expected 422 from validation, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body["detail"] == "Validation error"
    assert isinstance(body["errors"], list)
    assert len(body["errors"]) >= 1


@pytest.mark.asyncio
async def test_webhooks_cloud_metadata_returns_422(authed_client):
    client, api_key = authed_client

    resp = await client.post(
        "/v1/webhooks",
        headers={"X-Api-Key": api_key},
        json={
            "url": "http://169.254.169.254/latest/meta-data/",
            "event": "score.change",
            "threshold": 5,
        },
    )

    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"] == "Validation error"


@pytest.mark.asyncio
async def test_webhooks_http_not_https_returns_422(authed_client):
    """The validator has a second branch that rejects http:// — this
    ValueError path was also broken pre-fix."""
    client, api_key = authed_client

    resp = await client.post(
        "/v1/webhooks",
        headers={"X-Api-Key": api_key},
        json={
            "url": "http://example.com/hook",
            "event": "score.change",
            "threshold": 5,
        },
    )

    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"] == "Validation error"


@pytest.mark.asyncio
async def test_webhooks_valid_https_url_still_accepted(authed_client):
    """Regression guard: the fix must not break the happy path."""
    client, api_key = authed_client

    resp = await client.post(
        "/v1/webhooks",
        headers={"X-Api-Key": api_key},
        json={
            "url": "https://example.com/hook",
            "event": "score.change",
            "threshold": 5,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["url"] == "https://example.com/hook"
    assert body["is_active"] is True
    assert "secret" in body  # HMAC signing secret returned once
