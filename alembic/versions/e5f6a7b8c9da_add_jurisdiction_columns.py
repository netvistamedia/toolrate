"""add jurisdiction columns to tools

Revision ID: e5f6a7b8c9da
Revises: d4e5f6a7b8c9
Create Date: 2026-04-12 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9da"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tools", sa.Column("hosting_country", sa.String(2), nullable=True))
    op.add_column("tools", sa.Column("hosting_region", sa.String(64), nullable=True))
    op.add_column("tools", sa.Column("hosting_provider", sa.String(128), nullable=True))
    op.add_column("tools", sa.Column("jurisdiction_category", sa.String(32), nullable=True))
    op.create_index(
        "idx_tools_jurisdiction_category", "tools", ["jurisdiction_category"]
    )
    op.create_index(
        "idx_tools_category_jurisdiction", "tools", ["category", "jurisdiction_category"]
    )


def downgrade() -> None:
    op.drop_index("idx_tools_category_jurisdiction", "tools")
    op.drop_index("idx_tools_jurisdiction_category", "tools")
    op.drop_column("tools", "jurisdiction_category")
    op.drop_column("tools", "hosting_provider")
    op.drop_column("tools", "hosting_region")
    op.drop_column("tools", "hosting_country")
