import asyncio
import hashlib
import logging

import stripe
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import select, func, delete

from app.dependencies import Db, RedisClient, AuthenticatedKey
from app.core.security import generate_api_key
from app.models.api_key import ApiKey
from app.models.report import ExecutionReport
from app.models.webhook import Webhook
from app.config import settings
from app.services.audit import log_audit

router = APIRouter()
logger = logging.getLogger("nemoflow.auth")

# Strong references to in-flight welcome-email tasks so asyncio's weak-ref
# GC can't collect them mid-send. See the note in app/services/payg_meter.py.
_pending_welcome_tasks: set[asyncio.Task] = set()


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., max_length=256, description="Your email address (hashed, never stored in plain text)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"email": "dev@example.com"},
            ]
        }
    }


class RegisterResponse(BaseModel):
    api_key: str = Field(..., description="Your API key. Save it now — it cannot be retrieved later.")
    tier: str
    daily_limit: int
    message: str
    docs_url: str = Field("https://api.toolrate.ai/docs", description="Interactive API documentation")
    quickstart: str = Field(..., description="Copy-paste first API call example")


@router.post("/auth/register", response_model=RegisterResponse, tags=["Auth"],
             summary="Register for an API key",
             description="Create a free-tier API key. One key per email address. "
                         "Your email is hashed — we never store it in plain text.")
async def register(
    body: RegisterRequest,
    db: Db,
    redis: RedisClient,
    request: Request,
):
    # Rate limit registration: max 5 per IP per hour. Atomic INCR+EXPIRE so a
    # crash between the two commands can't leave the counter without a TTL
    # and permanently lock out the IP.
    client_ip = request.client.host if request.client else "unknown"
    reg_key = f"reg:ip:{client_ip}"
    _INCR_WITH_TTL_LUA = (
        "local c = redis.call('INCR', KEYS[1]); "
        "if c == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end; return c"
    )
    count = await redis.eval(_INCR_WITH_TTL_LUA, 1, reg_key, 3600)
    if count > 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registrations from this IP. Try again later.",
        )

    # Hash email for privacy + dedup
    email_hash = hashlib.sha256(body.email.lower().strip().encode()).hexdigest()

    # Check if email already registered. We store the email hash in the
    # `data_pool` field as `email:<hash>` for free keys. Only ACTIVE keys
    # count — after a rotate-key or account-delete, the old row is retained
    # for audit with `is_active=False`. Without the active filter a retried
    # registration after rotation would hit `MultipleResultsFound` and 500
    # instead of returning a clean 409.
    email_tag = f"email:{email_hash[:16]}"

    # Concurrent same-email registrations used to race past the SELECT below
    # and both create active free keys (= doubled quota). Postgres can't
    # express the constraint cleanly because `data_pool` is multi-purpose
    # (email tag, enterprise pool name, NULL), so we serialize the
    # check-and-insert window with a Redis SET NX lock keyed on the tag.
    # 30s TTL is plenty for the request to complete and short enough that a
    # crashed process doesn't lock out a retry for long.
    lock_key = f"reg:lock:{email_tag}"
    got_lock = await redis.set(lock_key, "1", ex=30, nx=True)
    if not got_lock:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A registration for this email is already in progress. Please wait a moment and try again.",
        )

    try:
        result = await db.execute(
            select(ApiKey).where(
                ApiKey.data_pool == email_tag,
                ApiKey.is_active == True,  # noqa: E712
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An API key already exists for this email. Contact support if you lost your key.",
            )

        # Create free-tier key
        full_key, key_hash, key_prefix = generate_api_key()
        api_key = ApiKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            tier="free",
            daily_limit=settings.free_daily_limit,
            data_pool=email_tag,
        )
        db.add(api_key)
        await log_audit(db, "key_created", actor_key_prefix=key_prefix,
                        resource_type="api_key", resource_id=key_prefix,
                        detail={"tier": "free"}, client_ip=client_ip)
        await db.commit()
    finally:
        # Release immediately on success/failure — the 30s TTL is just a
        # safety net for crashed workers.
        await redis.delete(lock_key)

    # Send welcome email (fire-and-forget, don't block registration).
    # Hold a strong reference to the task in a module-level set — asyncio
    # only keeps weak refs, so a bare create_task() can be GC'd mid-flight
    # and the email silently lost.
    import asyncio
    import logging as _logging
    from app.services.email import send_welcome_email

    async def _safe_send():
        try:
            await send_welcome_email(body.email, key_prefix)
        except Exception as e:
            _logging.getLogger("nemoflow.auth").warning("Welcome email failed for %s***: %s", body.email[:3], e)

    task = asyncio.create_task(_safe_send())
    _pending_welcome_tasks.add(task)
    task.add_done_callback(_pending_welcome_tasks.discard)

    quickstart = (
        f"# ── Install ToolRate ─────────────────────────────────────────\n"
        f"#\n"
        f"# Recommended (modern & fastest):\n"
        f"#   curl -LsSf https://astral.sh/uv/install.sh | sh   # one-time\n"
        f"#   uv add toolrate\n"
        f"#\n"
        f"# Alternative (without uv):\n"
        f"#   python3 -m venv .venv\n"
        f"#   source .venv/bin/activate\n"
        f"#   pip install toolrate\n"
        f"#\n"
        f"# Note: a bare `pip install toolrate` triggers PEP 668\n"
        f"# 'externally-managed-environment' on macOS Homebrew and\n"
        f"# recent Linux distros. Use one of the methods above instead.\n"
        f"# ─────────────────────────────────────────────────────────────\n\n"
        f"from toolrate import ToolRate\n"
        f"client = ToolRate(\"{key_prefix}...\")\n"
        f"print(client.assess(\"https://api.stripe.com/v1/charges\"))"
    )

    return RegisterResponse(
        api_key=full_key,
        tier="free",
        daily_limit=settings.free_daily_limit,
        message="Save this key now — it cannot be retrieved later. Upgrade to Pro at https://toolrate.ai",
        quickstart=quickstart,
    )


class RotateKeyResponse(BaseModel):
    new_api_key: str = Field(..., description="Your new API key. Save it now — it cannot be retrieved later.")
    old_key_prefix: str = Field(..., description="Prefix of the deactivated key")
    tier: str
    daily_limit: int


@router.post("/auth/rotate-key", response_model=RotateKeyResponse, tags=["Auth"],
             summary="Rotate your API key",
             description="Generate a new API key and deactivate the current one. "
                         "Your tier, limits, and billing remain unchanged.")
async def rotate_key(
    db: Db,
    api_key: AuthenticatedKey,
):
    old_prefix = api_key.key_prefix

    # Generate new key
    full_key, key_hash, key_prefix = generate_api_key()

    # Create new key with same settings. `billing_period` has to be copied
    # explicitly — the column default is "daily", so a Pro key (monthly)
    # that's rotated without this would silently become a daily-quota key,
    # turning a 10k/month quota into effectively 10k/day.
    new_key = ApiKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        tier=api_key.tier,
        daily_limit=api_key.daily_limit,
        billing_period=api_key.billing_period,
        data_pool=api_key.data_pool,
        stripe_customer_id=api_key.stripe_customer_id,
        stripe_subscription_id=api_key.stripe_subscription_id,
        stripe_subscription_item_id=api_key.stripe_subscription_item_id,
    )
    db.add(new_key)

    # Deactivate old key
    api_key.is_active = False

    # Migrate webhooks to new key
    from sqlalchemy import update
    await db.execute(
        update(Webhook).where(Webhook.api_key_id == api_key.id).values(api_key_id=new_key.id)
    )

    await log_audit(db, "key_rotated", actor_key_prefix=old_prefix,
                    resource_type="api_key", resource_id=key_prefix,
                    detail={"old_prefix": old_prefix, "new_prefix": key_prefix})
    await db.commit()

    return RotateKeyResponse(
        new_api_key=full_key,
        old_key_prefix=old_prefix,
        tier=new_key.tier,
        daily_limit=new_key.daily_limit,
    )


@router.delete("/account", tags=["Auth"],
               summary="Delete your account and all data",
               description="Permanently delete your API key and all associated data "
                           "(reports, webhooks). This action cannot be undone. GDPR Article 17 compliant.")
async def delete_account(
    db: Db,
    api_key: AuthenticatedKey,
):
    # Snapshot the billing attachment BEFORE we touch the key — we need it
    # for the Stripe cancel call and for the audit trail.
    had_subscription = bool(api_key.stripe_subscription_id)
    subscription_id_to_cancel = api_key.stripe_subscription_id

    canceled_subscription_id: str | None = None
    stripe_cancel_error: str | None = None

    # Best-effort Stripe subscription cancel. A Stripe outage or a 404 on an
    # already-canceled subscription must NOT block the account delete — GDPR
    # Article 17 requires us to honour the erasure request regardless of what
    # the downstream billing provider does. The error is captured in the
    # audit log so we can reconcile manually if needed.
    if had_subscription and settings.stripe_secret_key:
        try:
            await asyncio.to_thread(
                stripe.Subscription.cancel,
                subscription_id_to_cancel,
                api_key=settings.stripe_secret_key,
            )
            canceled_subscription_id = subscription_id_to_cancel
            logger.info(
                "Canceled Stripe subscription %s during account delete for key %s",
                subscription_id_to_cancel, api_key.key_prefix,
            )
        except Exception as e:
            stripe_cancel_error = str(e)[:200]
            logger.warning(
                "Stripe cancel failed during account delete for key %s "
                "(sub=%s): %s — proceeding with delete regardless",
                api_key.key_prefix, subscription_id_to_cancel, e,
            )
    elif had_subscription and not settings.stripe_secret_key:
        stripe_cancel_error = "stripe_not_configured"
        logger.warning(
            "Account %s had subscription %s but Stripe is not configured "
            "— subscription NOT canceled, manual reconciliation required",
            api_key.key_prefix, subscription_id_to_cancel,
        )

    # Delete webhooks
    await db.execute(delete(Webhook).where(Webhook.api_key_id == api_key.id))

    # Deactivate the key and clear all billing attachments. Without clearing
    # the Stripe IDs here the deleted account would still be reachable via
    # future Stripe webhooks (subscription_updated on a ghost key), and
    # the key→identity link would technically survive the erasure.
    api_key.is_active = False
    api_key.data_pool = None  # Remove email hash
    api_key.stripe_customer_id = None
    api_key.stripe_subscription_id = None
    api_key.stripe_subscription_item_id = None

    audit_detail: dict = {"had_subscription": had_subscription}
    if canceled_subscription_id:
        audit_detail["stripe_subscription_canceled"] = canceled_subscription_id
    if stripe_cancel_error:
        audit_detail["stripe_cancel_error"] = stripe_cancel_error

    await log_audit(
        db, "account_deleted",
        actor_key_prefix=api_key.key_prefix,
        resource_type="api_key",
        resource_id=api_key.key_prefix,
        detail=audit_detail,
    )
    await db.commit()

    return {
        "status": "deleted",
        "message": "Your API key has been deactivated and associated data removed.",
    }
