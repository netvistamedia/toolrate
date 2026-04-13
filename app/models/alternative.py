import uuid

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Alternative(Base):
    __tablename__ = "alternatives"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tool_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tools.id", ondelete="CASCADE"), nullable=False)
    alternative_tool_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tools.id", ondelete="CASCADE"), nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.5)
    # LLM-supplied reason this alternative is a good substitute for the parent
    # tool. Surfaced as `top_alternatives[i].reason` in /v1/assess responses.
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
