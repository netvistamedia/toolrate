import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Float, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class ScoreSnapshot(Base):
    __tablename__ = "score_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tool_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tools.id"), nullable=False)
    context_hash: Mapped[str] = mapped_column(String(64), default="__global__")
    data_pool: Mapped[str | None] = mapped_column(String(128))
    reliability_score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    success_rate_7d: Mapped[float] = mapped_column(Float)
    success_rate_30d: Mapped[float] = mapped_column(Float)
    total_reports: Mapped[int] = mapped_column(Integer)
    reports_7d: Mapped[int] = mapped_column(Integer)
    avg_latency_ms: Mapped[float | None] = mapped_column(Float)
    p95_latency_ms: Mapped[float | None] = mapped_column(Float)
    common_failure_categories: Mapped[dict | None] = mapped_column(JSON)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint("tool_id", "context_hash", "data_pool", name="uq_snapshot_tool_context_pool"),
    )
