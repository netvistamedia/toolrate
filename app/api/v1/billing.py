import asyncio
import logging
import uuid as _uuid

import httpx
import stripe
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, update

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
        customer = await asyncio.to_thread(
            stripe.Customer.create,
            api_key=sk,
            metadata={"api_key_id": str(api_key.id), "key_prefix": api_key.key_prefix},
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


@router.post("/billing/webhook", tags=["Billing"], include_in_schema=False)
async def stripe_webhook(request: Request, db: Db):
    """Handle Stripe webhook events for subscription lifecycle."""
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

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info("Stripe event: %s", event_type)

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(db, data)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(db, data)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, data)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(db, data)

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


async def _handle_checkout_completed(db, session):
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

    values = _plan_values(plan) | {
        "stripe_customer_id": customer_id,
        "stripe_subscription_id": subscription_id,
    }
    await db.execute(update(ApiKey).where(ApiKey.id == key_uuid).values(**values))
    await log_audit(
        db, f"upgraded_to_{plan}", resource_type="api_key",
        resource_id=api_key_id, detail={"subscription_id": subscription_id},
    )
    await db.commit()
    logger.info("Upgraded API key %s to %s (sub %s)", api_key_id, plan, subscription_id)


async def _handle_subscription_updated(db, subscription):
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
        logger.warning("Subscription %s → %s, downgraded to free limits", subscription_id, status)


async def _handle_subscription_deleted(db, subscription):
    """Downgrade to free when a subscription is cancelled. Skips enterprise."""
    subscription_id = subscription["id"]

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
    logger.info("Downgraded subscription %s to free tier", subscription_id)


async def _handle_payment_failed(db, invoice):
    """Log payment failure — Stripe retries automatically."""
    customer_id = invoice.get("customer")
    logger.warning("Payment failed for customer %s", customer_id)
