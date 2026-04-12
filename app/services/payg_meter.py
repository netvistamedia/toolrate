"""PAYG usage metering — reports overage to Stripe Billing Meters."""
import asyncio
import logging
from datetime import datetime, timezone

import stripe
from redis.asyncio import Redis

from app.config import settings
from app.models.api_key import ApiKey

logger = logging.getLogger("nemoflow.payg")

# Retain daily assessment counters long enough for the customer dashboard
# (`/v1/me/dashboard`) to read a 30-day history. 35 days gives a small
# buffer for calendar alignment.
ASSESS_DAILY_TTL_SECONDS = 35 * 24 * 3600


async def record_assessment(redis: Redis, api_key: ApiKey) -> dict:
    """Called once per billable /v1/assess call. Returns an info dict used by
    the response headers so clients can see where they are in their plan.

    For PAYG keys, the first `payg_free_daily_calls` per UTC day are free;
    every call beyond that is reported to Stripe as a meter event (fire-and-
    forget, so scoring latency is unaffected).
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
            asyncio.create_task(_report_meter_event(api_key))

    return info


async def _report_meter_event(api_key: ApiKey):
    """Fire a single Stripe Meter Event. Safe to call without configuration —
    logs a debug line and returns."""
    if not settings.stripe_secret_key or not settings.stripe_payg_price_id:
        logger.debug("PAYG metering skipped — Stripe not configured")
        return
    if not api_key.stripe_customer_id:
        logger.warning(
            "PAYG overage for key %s but no stripe_customer_id", api_key.key_prefix
        )
        return

    try:
        await asyncio.to_thread(
            stripe.billing.MeterEvent.create,
            api_key=settings.stripe_secret_key,
            event_name=settings.stripe_payg_meter_event_name,
            payload={
                "stripe_customer_id": api_key.stripe_customer_id,
                "value": "1",
            },
        )
    except Exception as e:
        # Never break a request because metering failed — the Redis buffer
        # still holds the count for reconciliation.
        logger.warning("Stripe meter event failed for %s: %s", api_key.key_prefix, e)
