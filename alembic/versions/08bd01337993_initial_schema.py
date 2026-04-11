"""initial schema

Revision ID: 08bd01337993
Revises:
Create Date: 2026-04-11 11:44:24.887670

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '08bd01337993'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tools
    op.create_table(
        'tools',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('identifier', sa.String(512), unique=True, nullable=False),
        sa.Column('display_name', sa.String(256), nullable=True),
        sa.Column('category', sa.String(128), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('report_count', sa.Integer, server_default='0'),
    )
    op.create_index('idx_tools_identifier', 'tools', ['identifier'], unique=True)

    # Execution reports
    op.create_table(
        'execution_reports',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('tool_id', UUID(as_uuid=True), sa.ForeignKey('tools.id'), nullable=False),
        sa.Column('success', sa.Boolean, nullable=False),
        sa.Column('error_category', sa.String(128), nullable=True),
        sa.Column('latency_ms', sa.Integer, nullable=True),
        sa.Column('context_hash', sa.String(64), server_default='__global__'),
        sa.Column('reporter_fingerprint', sa.String(64), nullable=False),
        sa.Column('data_pool', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('idx_reports_tool_context_created', 'execution_reports',
                    ['tool_id', 'context_hash', sa.text('created_at DESC')])
    op.create_index('idx_reports_tool_created', 'execution_reports',
                    ['tool_id', sa.text('created_at DESC')])
    op.create_index('idx_reports_fingerprint_created', 'execution_reports',
                    ['reporter_fingerprint', sa.text('created_at DESC')])

    # Score snapshots
    op.create_table(
        'score_snapshots',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('tool_id', UUID(as_uuid=True), sa.ForeignKey('tools.id'), nullable=False),
        sa.Column('context_hash', sa.String(64), server_default='__global__'),
        sa.Column('data_pool', sa.String(128), nullable=True),
        sa.Column('reliability_score', sa.Float, nullable=False),
        sa.Column('confidence', sa.Float, nullable=False),
        sa.Column('success_rate_7d', sa.Float, nullable=False),
        sa.Column('success_rate_30d', sa.Float, nullable=False),
        sa.Column('total_reports', sa.Integer, nullable=False),
        sa.Column('reports_7d', sa.Integer, nullable=False),
        sa.Column('avg_latency_ms', sa.Float, nullable=True),
        sa.Column('p95_latency_ms', sa.Float, nullable=True),
        sa.Column('common_failure_categories', sa.JSON, nullable=True),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.UniqueConstraint('tool_id', 'context_hash', 'data_pool', name='uq_snapshot_tool_context_pool'),
    )

    # API keys
    op.create_table(
        'api_keys',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('key_hash', sa.String(64), unique=True, nullable=False),
        sa.Column('key_prefix', sa.String(12), nullable=False),
        sa.Column('tier', sa.String(32), server_default='free'),
        sa.Column('daily_limit', sa.Integer, server_default='100'),
        sa.Column('data_pool', sa.String(128), nullable=True),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_api_keys_hash', 'api_keys', ['key_hash'], unique=True)

    # Alternatives
    op.create_table(
        'alternatives',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('tool_id', UUID(as_uuid=True), sa.ForeignKey('tools.id'), nullable=False),
        sa.Column('alternative_tool_id', UUID(as_uuid=True), sa.ForeignKey('tools.id'), nullable=False),
        sa.Column('relevance_score', sa.Float, server_default='0.5'),
    )


def downgrade() -> None:
    op.drop_table('alternatives')
    op.drop_table('api_keys')
    op.drop_table('score_snapshots')
    op.drop_table('execution_reports')
    op.drop_table('tools')
