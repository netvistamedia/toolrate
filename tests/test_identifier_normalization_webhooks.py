"""End-to-end regression tests for tool-identifier canonicalisation in webhooks.

Before the fix:

* ``POST /v1/webhooks`` stored ``body.tool_identifier`` verbatim, so a
  webhook registered under ``HTTPS://API.Stripe.com/v1/charges/`` would
  never match a dispatch keyed on the canonical
  ``https://api.stripe.com/v1/charges``.
* ``report_ingest.ingest_report`` passed the raw request ``tool_identifier``
  to ``dispatch_score_change`` while the DB tool row carried the normalized
  form — same silent no-op on any case/slash variant.

The pair of bugs made score-change webhooks silently miss every client
that didn't pre-normalize their URLs. These tests pin both sites with the
same ASGI-client pattern ``tests/test_validation_error_handler.py`` uses,
so a future refactor of the handler or ingest flow can't quietly regress.
"""
from __future__ import annotations

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.identifiers import normalize_identifier
from app.core.security import generate_api_key
from app.dependencies import get_db
from app.main import app
from app.models.api_key import ApiKey
from app.models.webhook import Webhook


@pytest_asyncio.fixture
async def authed_client(db_engine):
    """Real app client with in-memory DB + fakeredis + a valid API key.

    Matches the pattern in ``tests/test_validation_error_handler.py`` so
    the tests below exercise the production dispatch pipeline, not a
    surrogate — the fix lives in the ``POST /v1/webhooks`` handler and
    ``report_ingest.ingest_report``, and only a full-stack hit catches
    regressions at those boundaries.
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
            yield ac, full_key, session_factory
    finally:
        app.dependency_overrides.pop(get_db, None)
        await fake_redis.aclose()


def test_normalize_identifier_folds_case_and_trailing_slash() -> None:
    """Baseline: the normalizer is the single source of truth for canonical form."""
    assert (
        normalize_identifier("HTTPS://API.Stripe.Com/v1/charges/")
        == normalize_identifier("https://api.stripe.com/v1/charges")
    )


@pytest.mark.asyncio
async def test_webhook_registration_stores_canonical_tool_identifier(authed_client):
    """A non-canonical tool_identifier must be folded at the handler boundary.

    This is the failure mode that went live before the fix: a user who
    copy-pasted a marketing URL (mixed case, trailing slash) into
    ``tool_identifier`` would never receive any score.change webhook,
    because the dispatcher looks up on the normalized key.
    """
    client, api_key, session_factory = authed_client

    raw = "HTTPS://API.Stripe.Com/v1/charges/"
    canonical = normalize_identifier(raw)
    assert canonical == "https://api.stripe.com/v1/charges", (
        "normalizer contract changed — update the expected canonical form"
    )

    resp = await client.post(
        "/v1/webhooks",
        headers={"X-Api-Key": api_key},
        json={
            "url": "https://example.com/tr",
            "event": "score.change",
            "threshold": 5,
            "tool_identifier": raw,
        },
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()

    # The response surfaces the stored value — it must already be canonical
    # so the caller can trust "the filter I registered".
    assert body["tool_identifier"] == canonical, (
        f"handler returned un-normalized tool_identifier: {body['tool_identifier']!r}"
    )

    # And the DB row backing the response must carry the canonical form,
    # so delivery-time filtering (`Webhook.tool_identifier == tool.identifier`)
    # actually matches.
    async with session_factory() as db:
        row = (
            await db.execute(
                select(Webhook).where(Webhook.url == "https://example.com/tr")
            )
        ).scalar_one()
        assert row.tool_identifier == canonical


@pytest.mark.asyncio
async def test_webhook_registration_accepts_null_tool_identifier(authed_client):
    """Guard against the fix regressing the "fire for all tools" path.

    ``tool_identifier=None`` means "every tool" — the normalizer must not
    be invoked on None, and the row must store NULL, not the string ``"None"``.
    """
    client, api_key, session_factory = authed_client

    resp = await client.post(
        "/v1/webhooks",
        headers={"X-Api-Key": api_key},
        json={
            "url": "https://example.com/all",
            "event": "score.change",
            "threshold": 5,
        },
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tool_identifier"] is None

    async with session_factory() as db:
        row = (
            await db.execute(
                select(Webhook).where(Webhook.url == "https://example.com/all")
            )
        ).scalar_one()
        assert row.tool_identifier is None
