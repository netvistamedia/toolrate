"""PAYG usage metering — reports overage to Stripe Billing Meters.

Crash-safe via an outbox table. Every billable assess writes a ``pending``
row to ``payg_meter_events`` synchronously, then schedules the Stripe send
in a background task. The send flips the row to ``sent`` only after Stripe
acknowledges the event; if anything fails between the Redis increment and
the Stripe acknowledgement (worker crash, network blip, Stripe outage),
the row stays ``pending`` and the retry sweep picks it up.

Without the outbox, a fire-and-forget ``asyncio.create_task`` could be GC'd
mid-flight or killed by a SIGTERM during deploy, silently undercharging
the customer with no way to reconstruct the lost events.
"""
import asyncio
import logging
from datetime import datetime, timezone

import stripe
from redis.asyncio import Redis
from sqlalchemy import select, update

from app.config import settings
from app.models.api_key import ApiKey
from app.models.payg_meter_event import PaygMeterEvent

logger = logging.getLogger("nemoflow.payg")

# Retain daily assessment counters long enough for the customer dashboard
# (`/v1/me/dashboard`) to read a 30-day history. 35 days gives a small
# buffer for calendar alignment.
ASSESS_DAILY_TTL_SECONDS = 35 * 24 * 3600

# Strong references to in-flight background sends. asyncio's event loop
# only keeps WEAK references, so a task we create_task() without holding
# on to can be garbage-collected mid-execution. The outbox row is durable,
# so this is no longer a correctness issue (a GC'd task just leaves a
# pending row for the retry sweep) — but holding the ref still gets us
# faster invoice updates in the common path.
_pending_meter_tasks: set[asyncio.Task] = set()

# Cap on the number of times we'll auto-retry a single outbox row. Beyond
# this, the row stays ``pending`` and ops gets to investigate. We don't
# flip to a terminal "failed" state because that would silently drop the
# bill — better to let the row sit visible than to write off revenue.
MAX_SEND_ATTEMPTS = 5


def _on_meter_task_done(task: asyncio.Task) -> None:
    _pending_meter_tasks.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.warning("PAYG meter task crashed: %s", exc, exc_info=exc)


async def record_assessment(redis: Redis, api_key: ApiKey) -> dict:
    """Called once per billable /v1/assess call. Returns an info dict used by
    the response headers so clients can see where they are in their plan.

    For PAYG keys, the first ``payg_free_daily_calls`` per UTC day are free;
    every call beyond that writes a ``pending`` row to the meter-event outbox
    and schedules a background send. The row is the durable record — even
    if the worker crashes before the Stripe call lands, the bill still gets
    paid on the next retry sweep.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_key = f"assess:{api_key.key_hash}:{today}"

    # Atomic incr+expire — same Lua as the rate limiter.
    count = await redis.eval(
        "local c = redis.call('INCR', KEYS[1]); "
        "if c == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end; return c",
        1, daily_key, ASSESS_DAILY_TTL_SECONDS,
    )

    info = {"assess_today": int(count), "billable": False}

    if api_key.tier == "payg":
        free_grant = settings.payg_free_daily_calls
        if count > free_grant:
            info["billable"] = True
            # Buffer a monthly total for observability / invoice reconciliation.
            await redis.eval(
                "local c = redis.call('INCR', KEYS[1]); "
                "if c == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end; return c",
                1,
                f"payg_billable:{api_key.key_hash}:{datetime.now(timezone.utc).strftime('%Y-%m')}",
                40 * 24 * 3600,
            )

            event_id = await _enqueue_outbox(api_key)
            if event_id is not None:
                task = asyncio.create_task(_attempt_send(event_id))
                _pending_meter_tasks.add(task)
                task.add_done_callback(_on_meter_task_done)

    return info


async def _enqueue_outbox(api_key: ApiKey) -> int | None:
    """Persist a pending meter event. Returns the row id, or None on skip.

    Uses its own DB session so the assess request's transaction state is
    irrelevant — the outbox row is committed independently the moment we
    decide the call is billable.
    """
    if not api_key.stripe_customer_id:
        # No customer = nothing to bill. Log loud because this should not
        # happen in production: a PAYG tier without stripe_customer_id is
        # a Stripe state machine bug or a manual DB edit.
        logger.warning(
            "PAYG overage for key %s but no stripe_customer_id — skipping bill",
            api_key.key_prefix,
        )
        return None

    from app.db.session import async_session

    async with async_session() as db:
        row = PaygMeterEvent(
            api_key_id=api_key.id,
            stripe_customer_id=api_key.stripe_customer_id,
            value=1,
            status="pending",
        )
        db.add(row)
        try:
            await db.commit()
        except Exception as e:
            logger.warning("PAYG outbox insert failed for %s: %s", api_key.key_prefix, e)
            return None
        await db.refresh(row)
        return row.id


async def _attempt_send(event_id: int) -> None:
    """Send a single outbox row to Stripe and update its status.

    Increments ``attempt_count`` whether the send succeeds or fails, so a
    chain of failures is observable in the row itself. Bails early if
    Stripe is not configured or the row is already sent (handles the race
    where the retry sweep and the per-request send fire concurrently).
    """
    if not settings.stripe_secret_key or not settings.stripe_payg_price_id:
        logger.debug("PAYG metering skipped — Stripe not configured")
        return

    from app.db.session import async_session

    async with async_session() as db:
        row = (
            await db.execute(
                select(PaygMeterEvent).where(PaygMeterEvent.id == event_id)
            )
        ).scalar_one_or_none()
        if row is None or row.status == "sent":
            return

        try:
            await asyncio.to_thread(
                stripe.billing.MeterEvent.create,
                api_key=settings.stripe_secret_key,
                event_name=settings.stripe_payg_meter_event_name,
                payload={
                    "stripe_customer_id": row.stripe_customer_id,
                    "value": str(row.value),
                },
            )
        except Exception as e:
            await db.execute(
                update(PaygMeterEvent)
                .where(PaygMeterEvent.id == event_id)
                .values(
                    attempt_count=PaygMeterEvent.attempt_count + 1,
                    last_error=str(e)[:500],
                )
            )
            await db.commit()
            logger.warning(
                "Stripe meter event %s failed (attempt %s): %s",
                event_id, row.attempt_count + 1, e,
            )
            return

        await db.execute(
            update(PaygMeterEvent)
            .where(PaygMeterEvent.id == event_id)
            .values(
                attempt_count=PaygMeterEvent.attempt_count + 1,
                status="sent",
                sent_at=datetime.now(timezone.utc),
                last_error=None,
            )
        )
        await db.commit()


async def flush_pending_meter_events(*, batch_size: int = 100) -> dict:
    """Retry every still-pending outbox row that hasn't blown the attempt cap.

    Designed to run from a cron / admin endpoint. Returns counts so the
    caller can log throughput. Skips rows whose ``attempt_count`` reached
    ``MAX_SEND_ATTEMPTS`` so a permanently broken row (revoked customer,
    stale meter event_name) doesn't burn retries forever.
    """
    from app.db.session import async_session

    sent = 0
    failed = 0
    skipped = 0

    async with async_session() as db:
        result = await db.execute(
            select(PaygMeterEvent)
            .where(
                PaygMeterEvent.status == "pending",
                PaygMeterEvent.attempt_count < MAX_SEND_ATTEMPTS,
            )
            .order_by(PaygMeterEvent.created_at.asc())
            .limit(batch_size)
        )
        rows = list(result.scalars().all())

    for row in rows:
        before_attempts = row.attempt_count
        await _attempt_send(row.id)
        async with async_session() as db:
            updated = (
                await db.execute(
                    select(PaygMeterEvent).where(PaygMeterEvent.id == row.id)
                )
            ).scalar_one_or_none()
        if updated is None:
            skipped += 1
        elif updated.status == "sent":
            sent += 1
        elif updated.attempt_count > before_attempts:
            failed += 1
        else:
            skipped += 1

    return {"processed": len(rows), "sent": sent, "failed": failed, "skipped": skipped}
