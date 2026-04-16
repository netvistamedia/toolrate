"""index alternatives.tool_id and alternative_tool_id

Revision ID: j0e1f2a3bcd
Revises: i9d0e1f2abbc
Create Date: 2026-04-16 11:00:00.000000

The alternatives table grew without indexes on either FK column. The hot
read path (``scoring._get_alternatives``) hits ``WHERE tool_id = ?`` on
every assess call that exits the cache, and the symmetric reverse-lookup
(``WHERE alternative_tool_id = ?``) shows up in admin queries. Without
the indexes both paths full-scan a table that already carries a few
thousand rows after the LLM bootstrap and grows monotonically as more
LLM-derived alternatives are imported.

Idempotent guard via ``CREATE INDEX IF NOT EXISTS`` is unavailable on
older PostgreSQL through Alembic's wrapper, so the migration just relies
on Alembic's revision tracking to avoid double-creation.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "j0e1f2a3bcd"
down_revision: Union[str, Sequence[str], None] = "i9d0e1f2abbc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_alternatives_tool_id",
        "alternatives",
        ["tool_id"],
    )
    op.create_index(
        "idx_alternatives_alternative_tool_id",
        "alternatives",
        ["alternative_tool_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_alternatives_alternative_tool_id", "alternatives")
    op.drop_index("idx_alternatives_tool_id", "alternatives")
