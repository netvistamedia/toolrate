"""PAYG meter outbox — crash-safe billing for Stripe Meter Events.

The legacy code did fire-and-forget ``asyncio.create_task`` after a Redis
INCR. A worker crash between the increment and the Stripe acknowledgement
silently undercharged the customer with no audit trail to reconstruct.
The outbox writes a ``pending`` row first, then sends — these tests pin
that contract: no row is left in ``sent`` until Stripe confirms, the row
survives a Stripe outage, and the retry sweep does the right thing.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models import Base
from app.models.api_key import ApiKey
from app.models.payg_meter_event import PaygMeterEvent
from app.services import payg_meter


TEST_DATABASE_URL = "sqlite+aiosqlite:///test_payg_outbox.db"


@pytest_asyncio.fixture
async def db_factory(monkeypatch):
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    monkeypatch.setattr(
        "app.db.session.async_session", session_factory, raising=False
    )

    yield session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def redis():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


async def _make_payg_key(db_factory, *, customer_id="cus_test_123") -> ApiKey:
    async with db_factory() as db:
        key = ApiKey(
            key_hash="payg_hash_" + uuid.uuid4().hex,
            key_prefix="nf_payg",
            tier="payg",
            daily_limit=settings.payg_daily_hard_cap,
            billing_period="daily",
            stripe_customer_id=customer_id,
        )
        db.add(key)
        await db.commit()
        await db.refresh(key)
    return key


@pytest.fixture
def stripe_configured(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(settings, "stripe_payg_price_id", "price_test_fake")
    monkeypatch.setattr(settings, "payg_free_daily_calls", 0)


class TestOutboxEnqueue:
    @pytest.mark.asyncio
    async def test_billable_call_writes_pending_row(
        self, db_factory, redis, stripe_configured, monkeypatch
    ):
        api_key = await _make_payg_key(db_factory)

        # Stub the actual send so the test only exercises the enqueue path.
        async def _no_send(_event_id):
            return None

        monkeypatch.setattr(payg_meter, "_attempt_send", _no_send)

        info = await payg_meter.record_assessment(redis, api_key)
        assert info["billable"] is True

        async with db_factory() as db:
            rows = (
                await db.execute(
                    select(PaygMeterEvent).where(PaygMeterEvent.api_key_id == api_key.id)
                )
            ).scalars().all()
        assert len(rows) == 1
        assert rows[0].status == "pending"
        assert rows[0].stripe_customer_id == "cus_test_123"
        assert rows[0].value == 1
        assert rows[0].sent_at is None

    @pytest.mark.asyncio
    async def test_no_customer_id_skips_outbox(
        self, db_factory, redis, stripe_configured
    ):
        """A PAYG key without stripe_customer_id is a Stripe-state-machine
        bug. We log loud, but don't write a meter event we can't bill."""
        api_key = await _make_payg_key(db_factory, customer_id=None)
        async with db_factory() as db:
            db_key = (
                await db.execute(select(ApiKey).where(ApiKey.id == api_key.id))
            ).scalar_one()
            db_key.stripe_customer_id = None
            await db.commit()
            await db.refresh(db_key)

        info = await payg_meter.record_assessment(redis, db_key)
        assert info["billable"] is True

        async with db_factory() as db:
            rows = (
                await db.execute(
                    select(PaygMeterEvent).where(
                        PaygMeterEvent.api_key_id == api_key.id
                    )
                )
            ).scalars().all()
        assert rows == []

    @pytest.mark.asyncio
    async def test_free_grant_calls_skip_outbox(self, db_factory, redis, monkeypatch):
        monkeypatch.setattr(settings, "payg_free_daily_calls", 100)
        monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")
        api_key = await _make_payg_key(db_factory)

        info = await payg_meter.record_assessment(redis, api_key)
        assert info["billable"] is False

        async with db_factory() as db:
            rows = (
                await db.execute(
                    select(PaygMeterEvent).where(
                        PaygMeterEvent.api_key_id == api_key.id
                    )
                )
            ).scalars().all()
        assert rows == []


class TestSendAndRetry:
    @pytest.mark.asyncio
    async def test_successful_send_marks_sent(
        self, db_factory, stripe_configured
    ):
        api_key = await _make_payg_key(db_factory)
        async with db_factory() as db:
            row = PaygMeterEvent(
                api_key_id=api_key.id,
                stripe_customer_id="cus_test_123",
                value=1,
                status="pending",
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            event_id = row.id

        with patch("stripe.billing.MeterEvent.create") as mock_create:
            mock_create.return_value = {"id": "evt_stripe"}
            await payg_meter._attempt_send(event_id)

        async with db_factory() as db:
            updated = (
                await db.execute(
                    select(PaygMeterEvent).where(PaygMeterEvent.id == event_id)
                )
            ).scalar_one()
        assert updated.status == "sent"
        assert updated.attempt_count == 1
        assert updated.sent_at is not None
        assert updated.last_error is None

    @pytest.mark.asyncio
    async def test_stripe_failure_keeps_row_pending_with_error(
        self, db_factory, stripe_configured
    ):
        """The failure path is what justifies the whole outbox: a Stripe blip
        must NOT lose the bill — the row stays pending for the next retry."""
        api_key = await _make_payg_key(db_factory)
        async with db_factory() as db:
            row = PaygMeterEvent(
                api_key_id=api_key.id,
                stripe_customer_id="cus_test_123",
                value=1,
                status="pending",
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            event_id = row.id

        with patch(
            "stripe.billing.MeterEvent.create",
            side_effect=RuntimeError("simulated Stripe outage"),
        ):
            await payg_meter._attempt_send(event_id)

        async with db_factory() as db:
            updated = (
                await db.execute(
                    select(PaygMeterEvent).where(PaygMeterEvent.id == event_id)
                )
            ).scalar_one()
        assert updated.status == "pending"
        assert updated.attempt_count == 1
        assert "Stripe outage" in (updated.last_error or "")

    @pytest.mark.asyncio
    async def test_already_sent_row_skipped(self, db_factory, stripe_configured):
        """Race: the per-request send and the retry sweep both fire on the
        same row. The second one must NOT double-bill."""
        api_key = await _make_payg_key(db_factory)
        async with db_factory() as db:
            row = PaygMeterEvent(
                api_key_id=api_key.id,
                stripe_customer_id="cus_test_123",
                status="sent",
                attempt_count=1,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            event_id = row.id

        with patch("stripe.billing.MeterEvent.create") as mock_create:
            await payg_meter._attempt_send(event_id)
            mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_flush_processes_pending_and_marks_sent(
        self, db_factory, stripe_configured
    ):
        api_key = await _make_payg_key(db_factory)
        async with db_factory() as db:
            for _ in range(3):
                db.add(
                    PaygMeterEvent(
                        api_key_id=api_key.id,
                        stripe_customer_id="cus_test_123",
                        status="pending",
                    )
                )
            await db.commit()

        with patch("stripe.billing.MeterEvent.create"):
            stats = await payg_meter.flush_pending_meter_events()

        assert stats["processed"] == 3
        assert stats["sent"] == 3
        async with db_factory() as db:
            statuses = {
                r.status
                for r in (
                    await db.execute(select(PaygMeterEvent))
                ).scalars().all()
            }
        assert statuses == {"sent"}

    @pytest.mark.asyncio
    async def test_flush_skips_rows_at_max_attempts(
        self, db_factory, stripe_configured
    ):
        """A row that's already burned MAX_SEND_ATTEMPTS sits idle until ops
        looks at it — never silently retried into oblivion."""
        api_key = await _make_payg_key(db_factory)
        async with db_factory() as db:
            db.add(
                PaygMeterEvent(
                    api_key_id=api_key.id,
                    stripe_customer_id="cus_test_123",
                    status="pending",
                    attempt_count=payg_meter.MAX_SEND_ATTEMPTS,
                )
            )
            await db.commit()

        with patch("stripe.billing.MeterEvent.create") as mock_create:
            stats = await payg_meter.flush_pending_meter_events()
            mock_create.assert_not_called()

        assert stats["processed"] == 0

    @pytest.mark.asyncio
    async def test_stripe_not_configured_no_op(self, db_factory, monkeypatch):
        monkeypatch.setattr(settings, "stripe_secret_key", "")
        monkeypatch.setattr(settings, "stripe_payg_price_id", "")
        api_key = await _make_payg_key(db_factory)
        async with db_factory() as db:
            row = PaygMeterEvent(
                api_key_id=api_key.id,
                stripe_customer_id="cus_test_123",
                status="pending",
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            event_id = row.id

        with patch("stripe.billing.MeterEvent.create") as mock_create:
            await payg_meter._attempt_send(event_id)
            mock_create.assert_not_called()

        # Row state untouched — the retry sweep can pick it up later when
        # Stripe is configured again.
        async with db_factory() as db:
            updated = (
                await db.execute(
                    select(PaygMeterEvent).where(PaygMeterEvent.id == event_id)
                )
            ).scalar_one()
        assert updated.status == "pending"
        assert updated.attempt_count == 0
