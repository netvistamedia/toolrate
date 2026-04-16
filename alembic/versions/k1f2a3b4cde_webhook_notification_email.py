"""add notification_email to webhooks

Revision ID: k1f2a3b4cde
Revises: j0e1f2a3bcd
Create Date: 2026-04-16 11:30:00.000000

Owner-supplied opt-in email for webhook auto-deactivate notifications.
Webhooks today are silently disabled after 10 consecutive failures with
no audit row, no email, and no dashboard surfacing — owners discover the
outage by chance. This column lets the dispatcher email the owner the
moment a webhook is auto-deactivated. Nullable so existing webhooks keep
working unchanged; the audit log entry runs regardless of whether an
email destination was provided.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k1f2a3b4cde"
down_revision: Union[str, Sequence[str], None] = "j0e1f2a3bcd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "webhooks",
        sa.Column("notification_email", sa.String(256), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("webhooks", "notification_email")
