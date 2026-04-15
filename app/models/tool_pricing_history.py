import uuid
from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class ToolPricingHistory(Base):
    """Append-only log of pricing snapshots for a tool.

    Every update to `tools.pricing` writes a row here *first*, then updates
    the live value. Rows are never mutated. This lets us audit how a tool's
    price moved over time and correlate changes with reliability swings.

    Source values: 'llm_estimated', 'manual', 'user_reported'.
    """

    __tablename__ = "tool_pricing_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tool_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pricing: Mapped[dict] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
