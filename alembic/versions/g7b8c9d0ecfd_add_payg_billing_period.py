"""add billing_period and payg fields to api_keys

Revision ID: g7b8c9d0ecfd
Revises: f6a7b8c9dbec
Create Date: 2026-04-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g7b8c9d0ecfd"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9dbec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "api_keys",
        sa.Column("billing_period", sa.String(16), nullable=False, server_default="daily"),
    )
    op.add_column(
        "api_keys",
        sa.Column("stripe_subscription_item_id", sa.String(64), nullable=True),
    )
    # Existing Pro keys were provisioned at 10k/day. Keep them on daily until
    # their next renewal — the new 10k/month quota only applies to new subs.
    op.execute("UPDATE api_keys SET billing_period = 'daily' WHERE billing_period IS NULL")


def downgrade() -> None:
    op.drop_column("api_keys", "stripe_subscription_item_id")
    op.drop_column("api_keys", "billing_period")
