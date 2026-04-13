import hashlib

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

    # Check if email already registered (by checking key_prefix pattern won't work,
    # so we store email hash in data_pool field as "email:<hash>" for free keys)
    email_tag = f"email:{email_hash[:16]}"
    result = await db.execute(
        select(ApiKey).where(ApiKey.data_pool == email_tag)
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

    # Send welcome email (fire-and-forget, don't block registration)
    import asyncio
    import logging as _logging
    from app.services.email import send_welcome_email

    async def _safe_send():
        try:
            await send_welcome_email(body.email, key_prefix)
        except Exception as e:
            _logging.getLogger("nemoflow.auth").warning("Welcome email failed for %s***: %s", body.email[:3], e)

    asyncio.create_task(_safe_send())

    quickstart = (
        f"# Install (we recommend uv: https://github.com/astral-sh/uv)\n"
        f"uv add toolrate\n"
        f"# Or with pip in a venv: python3 -m venv .venv && source .venv/bin/activate && pip install toolrate\n\n"
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
    # Delete webhooks
    await db.execute(delete(Webhook).where(Webhook.api_key_id == api_key.id))

    # Deactivate the key (keep the record briefly for audit, but mark inactive)
    api_key.is_active = False
    api_key.data_pool = None  # Remove email hash

    await log_audit(db, "account_deleted", actor_key_prefix=api_key.key_prefix,
                    resource_type="api_key", resource_id=api_key.key_prefix)
    await db.commit()

    return {
        "status": "deleted",
        "message": "Your API key has been deactivated and associated data removed.",
    }
