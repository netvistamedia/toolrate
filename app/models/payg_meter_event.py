"""Append-only outbox for Stripe Billing Meter events.

Every billable PAYG assess call writes one row here BEFORE attempting the
Stripe send. The status starts at ``pending`` and flips to ``sent`` only
after Stripe confirms it received the event. If the worker process crashes
between the Redis increment and the Stripe call, the outbox row survives
the restart and a retry sweep picks it up.

Integer PK (not BigInteger) is intentional — see CLAUDE.md: SQLite-backed
tests round-trip through this model and aiosqlite chokes on BigInteger
autoincrement. Volume is bounded by paying-customer call rate, so Integer
is comfortably enough for the foreseeable horizon.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class PaygMeterEvent(Base):
    __tablename__ = "payg_meter_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    api_key_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Snapshot at creation. The api_key.stripe_customer_id can change
    # (rotation, account-delete clearing it) — billing for an event we already
    # incremented for must not silently switch to the wrong customer.
    stripe_customer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # "pending" → not yet sent to Stripe; "sent" → confirmed by Stripe.
    # No "failed" terminal state — we keep retrying with backoff and treat
    # exhausted-retry rows as ops attention required, not as accepted loss.
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
