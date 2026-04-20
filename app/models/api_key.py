import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(12))
    # "free" | "payg" | "pro" | "enterprise"
    tier: Mapped[str] = mapped_column(String(32), default="free")
    # Interpreted by the rate limiter based on billing_period.
    # - free/payg/enterprise with period=daily: calls per UTC day
    # - pro with period=monthly: calls per UTC calendar month
    daily_limit: Mapped[int] = mapped_column(Integer, default=100)
    # "daily" | "monthly" — controls which Redis counter the rate limiter reads.
    billing_period: Mapped[str] = mapped_column(String(16), default="daily")
    data_pool: Mapped[str | None] = mapped_column(String(128))
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(64))
    stripe_subscription_item_id: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Provenance tag for analytics. Set at registration time, never updated.
    # Common values: "web" (landing page), "mcp" (@toolrate/mcp-server),
    # "cli" (admin-issued via app.cli), null for legacy keys created before
    # the column existed.
    source: Mapped[str | None] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
