"""Tests for /v1/billing/webhook Stripe event deduplication.

Stripe retries webhook events on any 5xx or timeout, so the same `event["id"]`
used to reach the handler chain multiple times and produce duplicate side
effects (audit rows, tier transitions, welcome emails). These tests exercise
the Redis-backed dedup and the compensating delete that keeps genuine handler
failures replayable.
"""

import json

import fakeredis.aioredis
import pytest
import pytest_asyncio
import stripe
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.v1.billing import _STRIPE_EVENT_DEDUP_TTL
from app.config import settings
from app.dependencies import get_db
from app.main import app
from app.models.api_key import ApiKey
from app.models.audit_log import AuditLog


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def billing_client(db_engine, monkeypatch):
    """FastAPI client with in-memory DB, fakeredis, and fake Stripe secrets.

    Monkeypatches `stripe.Webhook.construct_event` so each test can feed
    arbitrary event dicts without forging a valid HMAC signature. Individual
    tests that want to exercise signature failure override this patch again
    — pytest's monkeypatch is function-scoped and shared with the fixture.
    """
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app.state.redis = fake_redis
    app.dependency_overrides[get_db] = override_get_db

    # The endpoint short-circuits to 503 if either secret is unset.
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test_fake")

    # Skip real signature verification — the payload bytes *are* the event.
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        lambda payload, sig_header, secret, tolerance=None: json.loads(payload),
    )

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, session_factory, fake_redis
    finally:
        app.dependency_overrides.pop(get_db, None)
        await fake_redis.aclose()


# ── Helpers ────────────────────────────────────────────────────────────────


async def _insert_test_key(session_factory) -> ApiKey:
    key = ApiKey(
        key_hash="stripe-test-hash",
        key_prefix="nf_test",
        tier="free",
        daily_limit=100,
        billing_period="daily",
    )
    async with session_factory() as db:
        db.add(key)
        await db.commit()
        await db.refresh(key)
    return key


def _checkout_completed_event(api_key_id: str, event_id: str = "evt_test_001") -> dict:
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_session",
                "customer": "cus_test_customer",
                "subscription": "sub_test_subscription",
                "metadata": {"api_key_id": api_key_id, "plan": "pro"},
            }
        },
    }


async def _count_upgrade_audits(session_factory, api_key_id: str) -> int:
    async with session_factory() as db:
        rows = (
            await db.execute(
                select(AuditLog).where(
                    AuditLog.action == "upgraded_to_pro",
                    AuditLog.resource_id == api_key_id,
                )
            )
        ).scalars().all()
    return len(rows)


# ── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_first_delivery_upgrades_key_and_writes_audit(billing_client):
    """Happy path: a fresh event upgrades the key and leaves exactly one audit row."""
    ac, sf, redis = billing_client
    key = await _insert_test_key(sf)
    event = _checkout_completed_event(str(key.id))

    resp = await ac.post(
        "/v1/billing/webhook",
        content=json.dumps(event),
        headers={"stripe-signature": "irrelevant-because-monkeypatched"},
    )

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    # Tier was upgraded, Stripe IDs were attached
    async with sf() as db:
        upgraded = (
            await db.execute(select(ApiKey).where(ApiKey.id == key.id))
        ).scalar_one()
    assert upgraded.tier == "pro"
    assert upgraded.billing_period == "monthly"
    assert upgraded.stripe_customer_id == "cus_test_customer"
    assert upgraded.stripe_subscription_id == "sub_test_subscription"

    # Exactly one audit row for this key
    assert await _count_upgrade_audits(sf, str(key.id)) == 1

    # Dedup marker exists with the expected TTL window
    ttl = await redis.ttl("stripe:events:seen:evt_test_001")
    assert 0 < ttl <= _STRIPE_EVENT_DEDUP_TTL


@pytest.mark.asyncio
async def test_duplicate_delivery_is_deduplicated(billing_client):
    """Replayed event returns 200 but MUST NOT write a second audit row or
    re-run the handler. This is the regression the dedup guard exists for."""
    ac, sf, _redis = billing_client
    key = await _insert_test_key(sf)
    event = _checkout_completed_event(str(key.id), event_id="evt_test_dup")
    payload = json.dumps(event)

    # First delivery — processes normally
    first = await ac.post(
        "/v1/billing/webhook",
        content=payload,
        headers={"stripe-signature": "x"},
    )
    assert first.status_code == 200
    assert first.json() == {"status": "ok"}
    assert await _count_upgrade_audits(sf, str(key.id)) == 1

    # Second delivery — same event_id, must dedupe
    second = await ac.post(
        "/v1/billing/webhook",
        content=payload,
        headers={"stripe-signature": "x"},
    )
    assert second.status_code == 200
    assert second.json() == {"status": "ok", "deduplicated": True}

    # Side effects UNCHANGED — still exactly one audit row
    assert await _count_upgrade_audits(sf, str(key.id)) == 1


@pytest.mark.asyncio
async def test_handler_failure_clears_dedup_marker_so_retry_can_proceed(billing_client):
    """Handler crash must release the dedup marker so Stripe's next retry
    reaches us. Without the compensating delete, a transient DB error on
    first delivery would silently poison the event permanently."""
    ac, _sf, redis = billing_client

    # Missing api_key_id in metadata forces _handle_checkout_completed to
    # raise HTTPException(500) — exactly the "handler failure" path we need
    # the wrapper to compensate for.
    broken_event = {
        "id": "evt_test_broken",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {},
                "customer": "cus_x",
                "subscription": "sub_x",
            }
        },
    }

    resp = await ac.post(
        "/v1/billing/webhook",
        content=json.dumps(broken_event),
        headers={"stripe-signature": "x"},
    )
    assert resp.status_code == 500

    # Marker MUST be gone — otherwise Stripe's retry would silently dedupe
    # and we'd never get a second chance at this event.
    assert await redis.get("stripe:events:seen:evt_test_broken") is None


@pytest.mark.asyncio
async def test_invalid_signature_returns_400_and_writes_no_marker(
    billing_client, monkeypatch
):
    """Unsigned / forged events are rejected before the dedup logic runs,
    so they can never pollute the Redis marker namespace."""
    ac, _sf, redis = billing_client

    def _fail(payload, sig_header, secret, tolerance=None):
        raise stripe.SignatureVerificationError("bad signature", sig_header)

    monkeypatch.setattr(stripe.Webhook, "construct_event", _fail)

    resp = await ac.post(
        "/v1/billing/webhook",
        content=b'{"id": "evt_never_seen", "type": "checkout.session.completed"}',
        headers={"stripe-signature": "bogus"},
    )
    assert resp.status_code == 400
    assert await redis.get("stripe:events:seen:evt_never_seen") is None


@pytest.mark.asyncio
async def test_unknown_event_type_still_marks_seen(billing_client):
    """Events we don't handle still return 200 and still get marked — else
    Stripe would retry them forever against an endpoint that will never act."""
    ac, _sf, redis = billing_client
    unknown = {
        "id": "evt_unknown_type",
        "type": "customer.created",
        "data": {"object": {}},
    }

    resp = await ac.post(
        "/v1/billing/webhook",
        content=json.dumps(unknown),
        headers={"stripe-signature": "x"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert await redis.get("stripe:events:seen:evt_unknown_type") == "1"
