"""add pricing column and tool_pricing_history table

Revision ID: i9d0e1f2abbc
Revises: h8c9d0e1fdaa
Create Date: 2026-04-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "i9d0e1f2abbc"
down_revision: Union[str, Sequence[str], None] = "h8c9d0e1fdaa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cost-aware scoring — pricing metadata for each tool. A single JSON column
    # keeps us flexible: per-call vs per-token vs freemium vs flat-monthly all
    # coexist without further migrations, and we can add fields like
    # tiered_thresholds later without touching this table. Shape is documented
    # on app/models/tool.py::Tool.pricing.
    op.add_column(
        "tools",
        sa.Column("pricing", sa.JSON(), nullable=True),
    )

    # Append-only history of pricing observations. The current price lives on
    # tools.pricing; every time we update it we first append a row here so we
    # can audit how a tool's price moved over time and correlate pricing
    # changes with reliability swings. Never updated in place.
    #
    # Integer PK (not BigInteger) matches CLAUDE.md's SQLite test constraint:
    # the model uses sa.Integer so tests can create the table via Base metadata
    # against aiosqlite. Append volume is low (≤600 tools × weekly refresh).
    op.create_table(
        "tool_pricing_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "tool_id",
            sa.Uuid(),
            sa.ForeignKey("tools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pricing", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # Composite index covers the only query shape we need:
    # "latest snapshot(s) for a given tool", via WHERE tool_id = ? ORDER BY
    # observed_at DESC LIMIT N. Cheaper than two separate indexes.
    op.create_index(
        "idx_tool_pricing_history_tool_observed",
        "tool_pricing_history",
        ["tool_id", "observed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_tool_pricing_history_tool_observed", "tool_pricing_history"
    )
    op.drop_table("tool_pricing_history")
    op.drop_column("tools", "pricing")
