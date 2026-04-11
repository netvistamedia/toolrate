"""add stripe fields to api_keys

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-11 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("stripe_customer_id", sa.String(64), nullable=True))
    op.add_column("api_keys", sa.Column("stripe_subscription_id", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("api_keys", "stripe_subscription_id")
    op.drop_column("api_keys", "stripe_customer_id")
