import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, Text, JSON
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

    # Per-tool mitigation overrides keyed by error category, e.g.
    # {"rate_limit": "Stripe enforces 100 req/s per account...", ...}.
    # Populated by the on-demand LLM assessment; scoring.compute_score prefers
    # these over the generic MITIGATIONS dict when present.
    mitigations_by_category: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Pricing metadata for cost-aware scoring. Shape:
    #   {
    #     "model": "per_call"|"per_token"|"flat_monthly"|"freemium"|"unknown",
    #     "base_usd_per_call": 0.01 | None,       # nullable; per_token APIs
    #                                             # leave this null and set
    #                                             # typical_usd_per_call
    #     "typical_usd_per_call": 0.02 | None,    # steady-state estimate used
    #                                             # for budget math; required
    #                                             # when base_usd_per_call is
    #                                             # null
    #     "estimated_tokens_per_call": 500 | None,# forward-compat; lets us
    #                                             # later do exact per-token
    #                                             # math without a migration
    #     "free_tier_per_month": 1000 | None,     # calls, not dollars
    #     "flat_monthly_usd": null | float,       # for subscription tools
    #     "currency": "USD",
    #     "source": "llm_estimated"|"manual"|"user_reported",
    #     "confidence": "high"|"medium"|"low",
    #     "notes": "Stripe: 2.9% + $0.30 per successful charge",
    #     "last_updated": "2026-04-15T00:00:00Z",
    #   }
    # Historical snapshots live in tool_pricing_history; this column is
    # always the current value, appended (never silently overwritten without
    # a history row first).
    pricing: Mapped[dict | None] = mapped_column(JSON, nullable=True)
