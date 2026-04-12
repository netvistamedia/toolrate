import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    identifier: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(256))
    category: Mapped[str | None] = mapped_column(String(128))
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    report_count: Mapped[int] = mapped_column(Integer, default=0)

    # Jurisdiction / GDPR metadata — populated by app/services/jurisdiction.py
    # via the three-tier hybrid resolver (seed → WHOIS → IP geolocation).
    hosting_country: Mapped[str | None] = mapped_column(String(2))
    hosting_region: Mapped[str | None] = mapped_column(String(64))
    hosting_provider: Mapped[str | None] = mapped_column(String(128))
    jurisdiction_category: Mapped[str | None] = mapped_column(String(32))
    jurisdiction_source: Mapped[str | None] = mapped_column(String(32))
    jurisdiction_confidence: Mapped[str | None] = mapped_column(String(16))
    notes: Mapped[str | None] = mapped_column(Text)
