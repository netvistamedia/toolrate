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
        # Concurrent reports for the same (fingerprint, session_id, attempt)
        # used to insert side-by-side, double-counting the journey in the
        # fallback chain analytics. The unique index enforces "one report per
        # attempt within a session for a given reporter". Both Postgres and
        # SQLite treat NULL as distinct in unique indexes, so legacy reports
        # without session/attempt data (both columns NULL) can coexist freely
        # — only rows that opt into journey tracking are de-duplicated.
        Index(
            "uq_reports_fingerprint_session_attempt",
            "reporter_fingerprint",
            "session_id",
            "attempt_number",
            unique=True,
        ),
    )
