"""add journey tracking fields

Revision ID: c5ff7924f07d
Revises: 08bd01337993
Create Date: 2026-04-11 13:44:39.795714

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5ff7924f07d'
down_revision: Union[str, Sequence[str], None] = '08bd01337993'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('execution_reports', sa.Column('session_id', sa.String(64), nullable=True))
    op.add_column('execution_reports', sa.Column('attempt_number', sa.Integer, nullable=True))
    op.add_column('execution_reports', sa.Column('previous_tool', sa.String(512), nullable=True))
    op.create_index('idx_reports_session', 'execution_reports', ['session_id'])
    op.create_index('idx_reports_previous_tool', 'execution_reports', ['previous_tool', sa.text('created_at DESC')])


def downgrade() -> None:
    op.drop_index('idx_reports_previous_tool', 'execution_reports')
    op.drop_index('idx_reports_session', 'execution_reports')
    op.drop_column('execution_reports', 'previous_tool')
    op.drop_column('execution_reports', 'attempt_number')
    op.drop_column('execution_reports', 'session_id')
