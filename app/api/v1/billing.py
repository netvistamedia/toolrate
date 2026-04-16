import asyncio
import logging
import uuid as _uuid
from datetime import datetime, timezone

import httpx
import stripe
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, EmailStr, Field
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import Db, AuthenticatedKey, RedisClient
from app.models.api_key import ApiKey
from app.services.audit import log_audit

# Atomic Redis INCR+EXPIRE so a crash between the two commands cannot leave
# a counter without a TTL and permanently lock out the IP. Shared by every
# unauthenticated endpoint that needs per-IP abuse protection.
_INCR_WITH_TTL_LUA = (
    "local c = redis.call('INCR', KEYS[1]); "
    "if c == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end; return c"
)

router = APIRouter()
logger = logging.getLogger("nemoflow.billing")


class ContactSalesRequest(BaseModel):
    email: EmailStr
    company: str = Field(min_length=1, max_length=120)
    volume: str = Field(min_length=1, max_length=64,
                        description="Estimated monthly call volume, e.g. '500k', '2M', 'unsure'")
    use_case: str = Field(min_length=10, max_length=2000,
                          description="What you're building and why you need ToolRate at scale")
    name: str | None = Field(default=None, max_length=120)


class ContactSalesResponse(BaseModel):
    status: str
    message: str


@router.post(
    "/billing/contact-sales",
    tags=["Billing"],
    response_model=ContactSalesResponse,
    summary="Request an Enterprise / Platform plan",
    description=(
        "Submit an inquiry for the Enterprise / Platform plan. "
        "Use this if you need a private data pool, SSO, SLA, white-label, "
        "or you are a platform (Cursor, Claude Code, Manus, etc.) that "
        "wants to enable ToolRate for all of your users."
    ),
)
async def contact_sales(request: Request, body: ContactSalesRequest, db: Db, redis: RedisClient):
    client_ip = request.client.host if request.client else "unknown"

    # Per-IP rate limit: 5 submissions/hour. Prevents form spam from flooding
    # the sales inbox and the audit log without any legitimate friction.
    rl_key = f"contact_sales:ip:{client_ip}"
    count = await redis.eval(_INCR_WITH_TTL_LUA, 1, rl_key, 3600)
    if count > 5:
        raise HTTPException(
            status_code=429,
            detail="Too many submissions from this IP. Please try again in an hour.",
        )

    logger.info(
        "Enterprise lead: company=%s email=%s volume=%s",
        body.company, body.email, body.volume,
    )

    await log_audit(
        db,
        "enterprise_lead_submitted",
        resource_type="contact_sales",
        detail={
            "email": body.email,
            "company": body.company,
            "volume": body.volume,
            "name": body.name,
            "use_case": body.use_case[:500],
        },
        client_ip=client_ip,
    )
    await db.commit()

    if settings.sendgrid_api_key and settings.sales_inbox_email:
        await _send_sales_email(body)

    return ContactSalesResponse(
        status="ok",
        message="Thanks — our team will reach out within one business day.",
    )


async def _send_sales_email(body: ContactSalesRequest):
    # HTML-escape every user-supplied field before inlining it into the email
    # body. Without this, a malicious `use_case` could inject arbitrary HTML
    # or phishing links into the inbox message delivered to the sales team.
    from html import escape
    company = escape(body.company)
    name = escape(body.name) if body.name else "—"
    email = escape(str(body.email))
    volume = escape(body.volume)
    use_case = escape(body.use_case)
    html = f"""
    <h2>New Enterprise / Platform lead</h2>
    <p><strong>Company:</strong> {company}</p>
    <p><strong>Name:</strong> {name}</p>
    <p><strong>Email:</strong> <a href="mailto:{email}">{email}</a></p>
    <p><strong>Est. volume:</strong> {volume}</p>
    <p><strong>Use case:</strong></p>
    <pre style="white-space:pre-wrap;font-family:inherit;background:#f5f5f5;padding:1rem;border-radius:8px">{use_case}</pre>
    """.strip()

    payload = {
        "personalizations": [{"to": [{"email": settings.sales_inbox_email}]}],
        "from": {"email": settings.sendgrid_from_email, "name": "ToolRate Leads"},
        "reply_to": {"email": str(body.email)},
        "subject": f"[ToolRate Enterprise] {body.company} — {body.volume}",
        "content": [{"type": "text/html", "value": html}],
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.sendgrid_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
        if resp.status_code >= 300:
            logger.warning("SendGrid sales email returned %s: %s", resp.status_code, resp.text)
    except Exception as e:
        logger.warning("Failed to send sales email: %s", e)


@router.post(
    "/billing/checkout",
    tags=["Billing"],
    summary="Create a Stripe Checkout session (PAYG or Pro)",
    description=(
        "Start a Stripe Checkout session for either the Pay-as-you-go plan "
        "(first 100 assessments/day free, then $0.008 each, no monthly "
        "commitment) or the Pro plan ($29/month for 10,000 assessments). "
        "Pass `?plan=payg` or `?plan=pro`. Default is `payg`."
    ),
)
async def create_checkout(
    db: Db,
    api_key: AuthenticatedKey,
    plan: str = "payg",
):
    if plan not in ("payg", "pro"):
        raise HTTPException(400, "plan must be 'payg' or 'pro'")
    if not settings.stripe_secret_key:
        raise HTTPException(503, "Billing is not configured")

    if plan == "pro" and api_key.tier == "pro" and api_key.stripe_subscription_id:
        raise HTTPException(400, "Already on Pro")
    if plan == "payg" and api_key.tier == "payg" and api_key.stripe_subscription_id:
        raise HTTPException(400, "Already on Pay-as-you-go")

    price_id = (
        settings.stripe_pro_price_id if plan == "pro" else settings.stripe_payg_price_id
    )
    if not price_id:
        raise HTTPException(503, f"{plan} pricing is not configured")

    sk = settings.stripe_secret_key

    if api_key.stripe_customer_id:
        customer_id = api_key.stripe_customer_id
    else:
        # Two concurrent checkouts for the same Free user used to create two
        # Stripe customers, with the second one's ID overwriting the first
        # in the DB. Stripe's idempotency_key folds both calls onto the same
        # customer record — Stripe's own retry-safety primitive, no DB lock
        # needed. Key shape is stable per api_key so retries within Stripe's
        # 24h idempotency window converge.
        customer = await asyncio.to_thread(
            stripe.Customer.create,
            api_key=sk,
            metadata={"api_key_id": str(api_key.id), "key_prefix": api_key.key_prefix},
            idempotency_key=f"customer-create-{api_key.id}",
        )
        customer_id = customer.id
        api_key.stripe_customer_id = customer_id
        await db.commit()

    # PAYG uses a metered price — line_items must NOT pass quantity.
    line_item = {"price": price_id}
    if plan == "pro":
        line_item["quantity"] = 1

    session = await asyncio.to_thread(
        stripe.checkout.Session.create,
        api_key=sk,
        customer=customer_id,
        mode="subscription",
        line_items=[line_item],
        success_url=f"https://toolrate.ai/billing/success?plan={plan}&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url="https://toolrate.ai/billing/cancel",
        metadata={"api_key_id": str(api_key.id), "plan": plan},
        subscription_data={"metadata": {"api_key_id": str(api_key.id), "plan": plan}},
    )

    return {"checkout_url": session.url, "session_id": session.id, "plan": plan}


# 30 days is well past Stripe's maximum retry window (~3 days) and gives a
# comfortable buffer for manual replays. 30 * 24 * 3600 = 2_592_000.
_STRIPE_EVENT_DEDUP_TTL = 2_592_000


@router.post("/billing/webhook", tags=["Billing"], include_in_schema=False)
async def stripe_webhook(request: Request, db: Db, redis: RedisClient):
    """Handle Stripe webhook events for subscription lifecycle.

    Stripe retries every event on a 5xx or timeout, so the same `event["id"]`
    will reach this endpoint multiple times during a flaky deploy or brief
    outage. Without deduplication every retry re-ran the full handler chain
    (double audit log rows, double tier transitions, double welcome emails).

    The fix is an atomic `SET NX` on `stripe:events:seen:<event_id>` right
    after signature verification. First delivery wins and proceeds; every
    replay returns 200 + `deduplicated: True` without touching the database.
    If the handler itself crashes we *remove* the marker before re-raising,
    so Stripe's retry is allowed through — otherwise a transient DB error
    on the first delivery would silently poison the event permanently.
    """
    if not settings.stripe_secret_key or not settings.stripe_webhook_secret:
        raise HTTPException(503, "Billing is not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(400, "Invalid webhook signature")

    event_id = event["id"]
    dedup_key = f"stripe:events:seen:{event_id}"

    # Atomic "have we seen this before?" — `set(..., nx=True)` returns a truthy
    # value only when the key was absent, which is exactly our first-seen
    # signal. redis-py's bool return means: True on SET, None on NX rejection.
    first_seen = await redis.set(dedup_key, "1", nx=True, ex=_STRIPE_EVENT_DEDUP_TTL)
    if not first_seen:
        logger.info(
            "Stripe event %s (%s) already processed — skipping replay",
            event_id,
            event["type"],
        )
        return {"status": "ok", "deduplicated": True}

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info("Stripe event: %s (id=%s)", event_type, event_id)

    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(db, redis, data)
        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(db, redis, data)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(db, redis, data)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(db, data)
    except Exception:
        # Handler crashed — release the dedup marker so Stripe's next retry
        # can reach us. Without this, the retry would hit the `not first_seen`
        # branch above and the event would be lost forever.
        await redis.delete(dedup_key)
        raise

    return {"status": "ok"}


def _plan_values(plan: str) -> dict:
    """Return the ApiKey column values for a given plan name."""
    if plan == "pro":
        return {
            "tier": "pro",
            "daily_limit": settings.pro_monthly_limit,
            "billing_period": "monthly",
        }
    # Default / payg: daily free grant is enforced in the app layer; the
    # `daily_limit` column acts as a safety cap.
    return {
        "tier": "payg",
        "daily_limit": settings.payg_daily_hard_cap,
        "billing_period": "daily",
    }


async def _reset_quota_counters(redis: Redis, key_hashes: list[str]) -> None:
    """Wipe both the daily and monthly Redis quota counters for these API keys.

    Called whenever an API key transitions between tiers (Stripe webhook
    handlers below). Without this reset, a Pro user who hit 9800/10000 monthly
    and got auto-downgraded for a failed payment, then re-upgraded after the
    retry succeeded, would land back on Pro with the monthly counter still
    reading 9800 — instant rate-limit on the very next assess. Symmetrically,
    a downgrade leaves the counter from the higher tier sitting in Redis
    until the period rolls over.

    Both daily and monthly keys are cleared regardless of direction. The
    "exploit" path (pay → cancel for free quota) doesn't open up because
    every counter the new tier reads is fresh anyway, and Stripe processing
    time alone makes this strictly worse than just waiting for the daily
    rollover.
    """
    if not key_hashes:
        return
    now = datetime.now(timezone.utc)
    keys: list[str] = []
    for kh in key_hashes:
        keys.append(f"rl:{kh}:m:{now.strftime('%Y-%m')}")
        keys.append(f"rl:{kh}:{now.strftime('%Y-%m-%d')}")
    await redis.delete(*keys)


async def _key_hashes_for_subscription(
    db: AsyncSession, subscription_id: str
) -> list[str]:
    """Look up every api_key.key_hash tied to a Stripe subscription.

    A subscription can in principle map to multiple API keys (key rotation
    leaves stripe_subscription_id pointing at the old row briefly), so the
    helper always returns a list — callers iterate.
    """
    result = await db.execute(
        select(ApiKey.key_hash).where(
            ApiKey.stripe_subscription_id == subscription_id,
        )
    )
    return [row[0] for row in result.all()]


async def _resolve_subscription_item_id(subscription_id: str | None) -> str | None:
    """Look up the first subscription_item_id for a Stripe subscription.

    PAYG metering needs the subscription_item_id to attach meter events;
    the rotation handler already copies it across, but the initial
    ``checkout.session.completed`` event never had it because Stripe only
    returns the subscription id in the session payload. Fetching it here
    keeps the column populated from day one instead of NULL until the
    customer rotates their key.

    Best-effort: a Stripe outage or 404 returns None and lets the audit
    flow continue. The retry sweep in payg_meter handles the missing-
    attachment case downstream.
    """
    if not subscription_id or not settings.stripe_secret_key:
        return None
    try:
        sub = await asyncio.to_thread(
            stripe.Subscription.retrieve,
            subscription_id,
            api_key=settings.stripe_secret_key,
        )
    except Exception as e:
        logger.warning(
            "Could not fetch subscription %s for item_id resolution: %s",
            subscription_id, e,
        )
        return None
    items = (sub.get("items") or {}).get("data") or []
    if not items:
        return None
    first = items[0]
    return first.get("id")


async def _handle_checkout_completed(db, redis: Redis, session):
    """Apply the plan the user just paid for."""
    meta = session.get("metadata") or {}
    api_key_id = meta.get("api_key_id")
    plan = meta.get("plan", "pro")  # Legacy sessions default to pro
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    if not api_key_id:
        logger.error("Checkout completed without api_key_id metadata — Stripe will retry")
        raise HTTPException(500, "Missing api_key_id in checkout metadata")

    try:
        key_uuid = _uuid.UUID(api_key_id)
    except ValueError:
        logger.error("Invalid api_key_id in checkout metadata: %s — Stripe will retry", api_key_id)
        raise HTTPException(500, "Invalid api_key_id in checkout metadata")

    subscription_item_id = await _resolve_subscription_item_id(subscription_id)

    values = _plan_values(plan) | {
        "stripe_customer_id": customer_id,
        "stripe_subscription_id": subscription_id,
        "stripe_subscription_item_id": subscription_item_id,
    }
    await db.execute(update(ApiKey).where(ApiKey.id == key_uuid).values(**values))
    await log_audit(
        db, f"upgraded_to_{plan}", resource_type="api_key",
        resource_id=api_key_id, detail={
            "subscription_id": subscription_id,
            "subscription_item_id": subscription_item_id,
        },
    )
    await db.commit()

    # Clear any stale daily counter from the previous tier. Pro reads the
    # monthly counter (fresh by construction at first checkout), but a free
    # user upgrading mid-day with 80/100 used would still see those 80 sitting
    # in Redis if they ever downgraded back to free same-day — keep the slate
    # clean from the start.
    key_row = await db.execute(select(ApiKey.key_hash).where(ApiKey.id == key_uuid))
    key_hash = key_row.scalar_one_or_none()
    if key_hash:
        await _reset_quota_counters(redis, [key_hash])

    logger.info("Upgraded API key %s to %s (sub %s)", api_key_id, plan, subscription_id)


async def _handle_subscription_updated(db, redis: Redis, subscription):
    """Handle subscription changes (plan change, renewal, pause).

    Enterprise keys are never touched — they're managed out-of-band and may
    carry a lingering Stripe subscription from a prior self-serve signup.
    """
    subscription_id = subscription["id"]
    status = subscription["status"]
    plan = (subscription.get("metadata") or {}).get("plan", "pro")

    if status == "active":
        values = _plan_values(plan)
        await db.execute(
            update(ApiKey)
            .where(
                ApiKey.stripe_subscription_id == subscription_id,
                ApiKey.tier != "enterprise",
            )
            .values(**values)
        )
        await db.commit()
        # Renewal-after-failure path: the previous month's counter may have
        # accumulated to the cap before the auto-downgrade. Without a reset
        # the renewed Pro key would re-hit the cap immediately.
        await _reset_quota_counters(
            redis, await _key_hashes_for_subscription(db, subscription_id),
        )
    elif status in ("past_due", "unpaid", "paused"):
        await db.execute(
            update(ApiKey)
            .where(
                ApiKey.stripe_subscription_id == subscription_id,
                ApiKey.tier != "enterprise",
            )
            .values(
                tier="free",
                daily_limit=settings.free_daily_limit,
                billing_period="daily",
            )
        )
        await db.commit()
        # Tier dropped from monthly to daily — the leftover monthly counter
        # is harmless to a fresh daily limiter, but the symmetric reset
        # keeps the contract simple: any tier transition = fresh counters.
        await _reset_quota_counters(
            redis, await _key_hashes_for_subscription(db, subscription_id),
        )
        logger.warning("Subscription %s → %s, downgraded to free limits", subscription_id, status)


async def _handle_subscription_deleted(db, redis: Redis, subscription):
    """Downgrade to free when a subscription is cancelled. Skips enterprise."""
    subscription_id = subscription["id"]

    # Snapshot the affected key_hashes BEFORE we null out stripe_subscription_id —
    # otherwise the lookup helper finds zero matches and we skip the reset.
    affected_hashes = await _key_hashes_for_subscription(db, subscription_id)

    await db.execute(
        update(ApiKey)
        .where(
            ApiKey.stripe_subscription_id == subscription_id,
            ApiKey.tier != "enterprise",
        )
        .values(
            tier="free",
            daily_limit=settings.free_daily_limit,
            billing_period="daily",
            stripe_subscription_id=None,
        )
    )
    await db.commit()
    await _reset_quota_counters(redis, affected_hashes)
    logger.info("Downgraded subscription %s to free tier", subscription_id)


async def _handle_payment_failed(db, invoice):
    """Log payment failure — Stripe retries automatically."""
    customer_id = invoice.get("customer")
    logger.warning("Payment failed for customer %s", customer_id)
