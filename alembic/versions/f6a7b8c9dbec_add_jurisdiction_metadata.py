"""add jurisdiction source/confidence/notes columns

Revision ID: f6a7b8c9dbec
Revises: e5f6a7b8c9da
Create Date: 2026-04-12 11:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9dbec"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Track where the jurisdiction verdict came from so callers can reason
    # about its trustworthiness. Stored as plain strings rather than real
    # Postgres ENUMs to stay SQLite-compatible (tests use SQLite).
    # Allowed values:
    #   jurisdiction_source     — 'manual', 'whois', 'ip_geolocation', 'cdn_detected'
    #   jurisdiction_confidence — 'high', 'medium', 'low'
    op.add_column("tools", sa.Column("jurisdiction_source", sa.String(32), nullable=True))
    op.add_column("tools", sa.Column("jurisdiction_confidence", sa.String(16), nullable=True))
    op.add_column("tools", sa.Column("notes", sa.Text(), nullable=True))
    op.create_index(
        "idx_tools_jurisdiction_source", "tools", ["jurisdiction_source"]
    )


def downgrade() -> None:
    op.drop_index("idx_tools_jurisdiction_source", "tools")
    op.drop_column("tools", "notes")
    op.drop_column("tools", "jurisdiction_confidence")
    op.drop_column("tools", "jurisdiction_source")
