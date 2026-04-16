"""add payg_meter_events outbox table

Revision ID: l2g3h4i5jkl
Revises: k1f2a3b4cde
Create Date: 2026-04-16 12:00:00.000000

Outbox for Stripe Billing Meter events. Today the assess handler fires a
``stripe.billing.MeterEvent.create`` via ``asyncio.create_task`` after
incrementing the Redis billable counter — if the worker crashes between
the increment and the Stripe call, the event is silently lost and the
customer is undercharged.

The outbox row is written synchronously when the call becomes billable.
A background sender flips the status to ``sent`` only after Stripe
acknowledges the event; if it fails, the row stays ``pending`` for the
retry sweep to pick up.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "l2g3h4i5jkl"
down_revision: Union[str, Sequence[str], None] = "k1f2a3b4cde"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payg_meter_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "api_key_id",
            sa.Uuid(),
            sa.ForeignKey("api_keys.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stripe_customer_id", sa.String(64), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_payg_meter_events_api_key_id",
        "payg_meter_events",
        ["api_key_id"],
    )
    # Retry sweep query shape: WHERE status = 'pending' ORDER BY created_at.
    op.create_index(
        "idx_payg_meter_events_status_created",
        "payg_meter_events",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_payg_meter_events_status_created", "payg_meter_events")
    op.drop_index("idx_payg_meter_events_api_key_id", "payg_meter_events")
    op.drop_table("payg_meter_events")
