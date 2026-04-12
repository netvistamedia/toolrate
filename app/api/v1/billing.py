import asyncio
import logging
import uuid as _uuid

import stripe
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select, update

from app.config import settings
from app.dependencies import Db, AuthenticatedKey
from app.models.api_key import ApiKey

router = APIRouter()
logger = logging.getLogger("nemoflow.billing")


@router.post("/billing/checkout", tags=["Billing"],
             summary="Create a Pro upgrade checkout session",
             description="Creates a Stripe Checkout session to upgrade to the Pro tier ($29/mo). "
                         "Returns a URL to redirect the user to complete payment.")
async def create_checkout(
    db: Db,
    api_key: AuthenticatedKey,
):
    if not settings.stripe_secret_key:
        raise HTTPException(503, "Billing is not configured")

    if api_key.tier == "pro" and api_key.stripe_subscription_id:
        raise HTTPException(400, "Already on Pro tier")

    sk = settings.stripe_secret_key

    # Create or reuse Stripe customer (run in thread to avoid blocking event loop)
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

    session = await asyncio.to_thread(
        stripe.checkout.Session.create,
        api_key=sk,
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": settings.stripe_pro_price_id, "quantity": 1}],
        success_url="https://api.nemoflow.ai/billing/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://api.nemoflow.ai/billing/cancel",
        metadata={"api_key_id": str(api_key.id)},
    )

    return {"checkout_url": session.url, "session_id": session.id}


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


async def _handle_checkout_completed(db, session):
    """Upgrade API key to pro after successful checkout."""
    api_key_id = session.get("metadata", {}).get("api_key_id")
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

    await db.execute(
        update(ApiKey)
        .where(ApiKey.id == key_uuid)
        .values(
            tier="pro",
            daily_limit=settings.pro_daily_limit,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
        )
    )
    from app.services.audit import log_audit
    await log_audit(db, "upgraded_to_pro", resource_type="api_key",
                    resource_id=api_key_id,
                    detail={"subscription_id": subscription_id})
    await db.commit()
    logger.info("Upgraded API key %s to pro (subscription %s)", api_key_id, subscription_id)


async def _handle_subscription_updated(db, subscription):
    """Handle subscription changes (e.g., plan change, renewal)."""
    subscription_id = subscription["id"]
    status = subscription["status"]

    if status == "active":
        await db.execute(
            update(ApiKey)
            .where(ApiKey.stripe_subscription_id == subscription_id)
            .values(tier="pro", daily_limit=settings.pro_daily_limit)
        )
        await db.commit()
    elif status in ("past_due", "unpaid", "paused"):
        # Restrict to free limits but keep subscription link for recovery
        await db.execute(
            update(ApiKey)
            .where(ApiKey.stripe_subscription_id == subscription_id)
            .values(tier="free", daily_limit=settings.free_daily_limit)
        )
        await db.commit()
        logger.warning("Subscription %s status changed to %s — downgraded to free limits", subscription_id, status)


async def _handle_subscription_deleted(db, subscription):
    """Downgrade to free when subscription is cancelled."""
    subscription_id = subscription["id"]

    await db.execute(
        update(ApiKey)
        .where(ApiKey.stripe_subscription_id == subscription_id)
        .values(
            tier="free",
            daily_limit=settings.free_daily_limit,
            stripe_subscription_id=None,
        )
    )
    await db.commit()
    logger.info("Downgraded subscription %s to free tier", subscription_id)


async def _handle_payment_failed(db, invoice):
    """Log payment failure — Stripe retries automatically."""
    customer_id = invoice.get("customer")
    logger.warning("Payment failed for customer %s", customer_id)
