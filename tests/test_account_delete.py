"""Tests for DELETE /v1/account — GDPR Article 17 erasure.

Regression tests for bug #4: the old handler marked the key inactive but
left `stripe_customer_id` / `stripe_subscription_id` / `stripe_subscription_item_id`
dangling, which meant the user kept getting billed after "account deleted"
and future Stripe webhooks could still re-read the erased account.

These tests verify the new flow:
  1. If there's an active subscription, the handler calls Stripe cancel
     (best-effort, wrapped in try/except so a Stripe outage doesn't block
     the delete).
  2. All three Stripe ID columns are cleared on the key.
  3. The audit log row captures the cancellation result so we can
     reconcile manually if Stripe was unavailable.
"""

import fakeredis.aioredis
import pytest
import pytest_asyncio
import stripe
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import settings
from app.core.security import generate_api_key
from app.dependencies import get_db
from app.main import app
from app.models.api_key import ApiKey
from app.models.audit_log import AuditLog


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def auth_client(db_engine, monkeypatch):
    """FastAPI client with in-memory DB, fakeredis, and Stripe configured."""
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app.state.redis = fake_redis
    app.dependency_overrides[get_db] = override_get_db

    # The new delete_account handler only attempts Stripe cancel when
    # `stripe_secret_key` is set. Give it a placeholder so the cancel
    # path is exercised — individual tests override this when they want
    # to simulate "Stripe not configured".
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, session_factory, fake_redis
    finally:
        app.dependency_overrides.pop(get_db, None)
        await fake_redis.aclose()


# ── Helpers ────────────────────────────────────────────────────────────────


async def _create_key(
    session_factory,
    *,
    with_subscription: bool = True,
    tier: str = "pro",
) -> tuple[str, ApiKey]:
    """Insert a test key and return (plaintext key, ORM instance)."""
    full, key_hash, prefix = generate_api_key()
    async with session_factory() as db:
        key = ApiKey(
            key_hash=key_hash,
            key_prefix=prefix,
            tier=tier,
            daily_limit=10_000,
            billing_period="monthly" if tier == "pro" else "daily",
            stripe_customer_id="cus_test_customer" if with_subscription else None,
            stripe_subscription_id="sub_test_active" if with_subscription else None,
            stripe_subscription_item_id="si_test_item" if with_subscription else None,
            is_active=True,
        )
        db.add(key)
        await db.commit()
        await db.refresh(key)
    return full, key


async def _reload_key(session_factory, key_id) -> ApiKey:
    async with session_factory() as db:
        return (
            await db.execute(select(ApiKey).where(ApiKey.id == key_id))
        ).scalar_one()


async def _get_delete_audit(session_factory, key_prefix: str) -> AuditLog | None:
    async with session_factory() as db:
        return (
            await db.execute(
                select(AuditLog).where(
                    AuditLog.action == "account_deleted",
                    AuditLog.resource_id == key_prefix,
                )
            )
        ).scalar_one_or_none()


# ── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_happy_path_cancels_stripe_subscription_and_clears_fields(
    auth_client, monkeypatch
):
    """Account with an active Stripe subscription should: cancel the sub,
    clear all three Stripe ID columns, and log the cancellation."""
    ac, sf, _redis = auth_client
    full_key, key = await _create_key(sf, with_subscription=True)

    # Track calls to stripe.Subscription.cancel
    cancel_calls: list[tuple[str, dict]] = []

    def fake_cancel(sub_id, **kwargs):
        cancel_calls.append((sub_id, kwargs))
        return {"id": sub_id, "status": "canceled"}

    monkeypatch.setattr(stripe.Subscription, "cancel", fake_cancel)

    resp = await ac.delete("/v1/account", headers={"X-Api-Key": full_key})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "deleted"

    # Stripe was called exactly once with the right subscription_id
    assert len(cancel_calls) == 1
    assert cancel_calls[0][0] == "sub_test_active"
    # Our code passes api_key=sk via kwargs so the Stripe SDK uses the
    # test key instead of the process-global one
    assert cancel_calls[0][1].get("api_key") == "sk_test_fake"

    # Key state post-delete: inactive, all Stripe IDs cleared, email hash gone
    refreshed = await _reload_key(sf, key.id)
    assert refreshed.is_active is False
    assert refreshed.stripe_customer_id is None
    assert refreshed.stripe_subscription_id is None
    assert refreshed.stripe_subscription_item_id is None
    assert refreshed.data_pool is None

    # Audit log entry captures the cancellation
    audit = await _get_delete_audit(sf, key.key_prefix)
    assert audit is not None
    assert audit.detail["had_subscription"] is True
    assert audit.detail["stripe_subscription_canceled"] == "sub_test_active"
    assert "stripe_cancel_error" not in audit.detail


@pytest.mark.asyncio
async def test_delete_without_subscription_skips_stripe_call(auth_client, monkeypatch):
    """Users without an active sub (e.g. free tier) delete cleanly without
    any Stripe API call — same audit entry, just `had_subscription=False`."""
    ac, sf, _redis = auth_client
    full_key, key = await _create_key(sf, with_subscription=False, tier="free")

    cancel_calls: list[str] = []

    def fake_cancel(sub_id, **kwargs):
        cancel_calls.append(sub_id)
        return {"id": sub_id, "status": "canceled"}

    monkeypatch.setattr(stripe.Subscription, "cancel", fake_cancel)

    resp = await ac.delete("/v1/account", headers={"X-Api-Key": full_key})
    assert resp.status_code == 200

    # Stripe should NOT have been touched
    assert cancel_calls == []

    refreshed = await _reload_key(sf, key.id)
    assert refreshed.is_active is False
    # Already-None fields are still None; the delete is idempotent-friendly
    assert refreshed.stripe_customer_id is None
    assert refreshed.stripe_subscription_id is None
    assert refreshed.stripe_subscription_item_id is None

    audit = await _get_delete_audit(sf, key.key_prefix)
    assert audit is not None
    assert audit.detail["had_subscription"] is False
    assert "stripe_subscription_canceled" not in audit.detail
    assert "stripe_cancel_error" not in audit.detail


@pytest.mark.asyncio
async def test_stripe_cancel_error_does_not_block_delete(auth_client, monkeypatch):
    """If Stripe is down or returns an error (e.g. subscription already
    canceled), the account delete MUST still complete. The error lands in
    the audit detail so we can reconcile later."""
    ac, sf, _redis = auth_client
    full_key, key = await _create_key(sf, with_subscription=True)

    def fake_cancel_boom(sub_id, **kwargs):
        raise Exception("No such subscription: sub_test_active")

    monkeypatch.setattr(stripe.Subscription, "cancel", fake_cancel_boom)

    resp = await ac.delete("/v1/account", headers={"X-Api-Key": full_key})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "deleted"

    # Critical: the delete MUST have proceeded despite the Stripe failure
    refreshed = await _reload_key(sf, key.id)
    assert refreshed.is_active is False
    assert refreshed.stripe_customer_id is None
    assert refreshed.stripe_subscription_id is None
    assert refreshed.stripe_subscription_item_id is None

    # Audit entry captures what Stripe said so an operator can reconcile
    audit = await _get_delete_audit(sf, key.key_prefix)
    assert audit is not None
    assert audit.detail["had_subscription"] is True
    assert "stripe_subscription_canceled" not in audit.detail
    assert audit.detail["stripe_cancel_error"].startswith("No such subscription")


@pytest.mark.asyncio
async def test_stripe_not_configured_is_recorded_as_manual_reconciliation(
    auth_client, monkeypatch
):
    """Edge case: key has a sub ID but the server lost its Stripe secret.
    The audit log must reflect that the sub was NOT canceled so ops can
    find and fix it — otherwise the sub silently keeps billing forever."""
    ac, sf, _redis = auth_client
    full_key, key = await _create_key(sf, with_subscription=True)

    # Turn Stripe "off" for this request
    monkeypatch.setattr(settings, "stripe_secret_key", "")

    def fake_cancel(sub_id, **kwargs):
        raise AssertionError("stripe.Subscription.cancel must not be called when Stripe is unconfigured")

    monkeypatch.setattr(stripe.Subscription, "cancel", fake_cancel)

    resp = await ac.delete("/v1/account", headers={"X-Api-Key": full_key})
    assert resp.status_code == 200

    refreshed = await _reload_key(sf, key.id)
    assert refreshed.is_active is False
    # Stripe fields still cleared on our side — we can't cancel the sub
    # but we CAN cut the tie between the deleted identity and the Stripe ID.
    assert refreshed.stripe_subscription_id is None

    audit = await _get_delete_audit(sf, key.key_prefix)
    assert audit is not None
    assert audit.detail["had_subscription"] is True
    assert audit.detail["stripe_cancel_error"] == "stripe_not_configured"
