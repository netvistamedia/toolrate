"""add source provenance column to api_keys

Revision ID: p6k7l8m9nop
Revises: o5j6k7l8mno
Create Date: 2026-04-20 14:50:00.000000

Adds a nullable ``source`` column to ``api_keys`` so we can attribute new
registrations to their channel: ``web`` (landing page form), ``mcp``
(via @toolrate/mcp-server's bootstrap register tool), ``cli``
(admin-issued), or future ``partner_<name>`` tags.

Existing keys are left with NULL — there's no reliable way to retro-fit
their provenance and "unknown" is the honest answer. Future registration
flows must pass the value at insert time; the column is intentionally
not back-filled.

Indexed because the primary use is GROUP BY in stats queries, not
filtering at request time.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "p6k7l8m9nop"
down_revision: Union[str, Sequence[str], None] = "o5j6k7l8mno"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "api_keys",
        sa.Column("source", sa.String(length=32), nullable=True),
    )
    op.create_index(
        "ix_api_keys_source",
        "api_keys",
        ["source"],
    )


def downgrade() -> None:
    op.drop_index("ix_api_keys_source", table_name="api_keys")
    op.drop_column("api_keys", "source")
