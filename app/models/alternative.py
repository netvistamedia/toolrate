import uuid

from sqlalchemy import Float, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Alternative(Base):
    __tablename__ = "alternatives"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tool_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tools.id"), nullable=False)
    alternative_tool_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tools.id"), nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.5)
