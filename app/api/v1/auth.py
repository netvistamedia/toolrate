import hashlib

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import select, func

from app.dependencies import Db, RedisClient
from app.core.security import generate_api_key
from app.models.api_key import ApiKey
from app.config import settings

router = APIRouter()


class RegisterRequest(BaseModel):
    email: str = Field(..., max_length=256, description="Your email address (hashed, never stored in plain text)")

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
    # Rate limit registration: max 5 per IP per hour
    client_ip = request.client.host if request.client else "unknown"
    reg_key = f"reg:ip:{client_ip}"
    count = await redis.incr(reg_key)
    if count == 1:
        await redis.expire(reg_key, 3600)
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
        select(ApiKey).where(ApiKey.data_pool == email_tag, ApiKey.tier == "free")
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
    await db.commit()

    return RegisterResponse(
        api_key=full_key,
        tier="free",
        daily_limit=settings.free_daily_limit,
        message="Save this key now — it cannot be retrieved later. Upgrade to Pro at https://nemoflow.ai",
    )
