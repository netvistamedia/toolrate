"""add tool-specific mitigations and alternative reason

Revision ID: h8c9d0e1fdaa
Revises: g7b8c9d0ecfd
Create Date: 2026-04-13 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h8c9d0e1fdaa"
down_revision: Union[str, Sequence[str], None] = "g7b8c9d0ecfd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Per-tool mitigation overrides keyed by error category. Populated by the
    # on-demand LLM assessment so we surface tool-specific advice instead of
    # the generic strings in scoring.MITIGATIONS.
    op.add_column(
        "tools",
        sa.Column("mitigations_by_category", sa.JSON(), nullable=True),
    )
    # The LLM's reason for suggesting an alternative (e.g. "Merchant of record
    # handles VAT/sales tax automatically"). Replaces the hardcoded
    # 'Alternative provider' string in /v1/assess responses.
    op.add_column(
        "alternatives",
        sa.Column("reason", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("alternatives", "reason")
    op.drop_column("tools", "mitigations_by_category")
