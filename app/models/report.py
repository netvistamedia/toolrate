import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class ExecutionReport(Base):
    __tablename__ = "execution_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tool_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tools.id", ondelete="CASCADE"), nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_category: Mapped[str | None] = mapped_column(String(128))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    context_hash: Mapped[str] = mapped_column(String(64), default="__global__")
    reporter_fingerprint: Mapped[str] = mapped_column(String(64))
    data_pool: Mapped[str | None] = mapped_column(String(128))
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    attempt_number: Mapped[int | None] = mapped_column(Integer)
    previous_tool: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        # Lookup index supporting the app-layer dedup check in
        # ``report_ingest.ingest_report`` — we can't add a UNIQUE constraint
        # because ``execution_reports`` is partitioned on ``created_at``
        # and Postgres requires unique indexes on partitioned tables to
        # include every partition key column. The pre-insert SELECT on
        # this index is cheap and the residual race window for true
        # concurrent inserts is small (microseconds).
        Index(
            "idx_reports_fingerprint_session_attempt",
            "reporter_fingerprint",
            "session_id",
            "attempt_number",
        ),
    )
