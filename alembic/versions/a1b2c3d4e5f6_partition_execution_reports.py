"""partition execution_reports by month

Revision ID: a1b2c3d4e5f6
Revises: c5ff7924f07d
Create Date: 2026-04-11 22:00:00.000000

Converts execution_reports to range-partitioned table on created_at.
Existing data is migrated into the appropriate monthly partition.
"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "c5ff7924f07d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Rename existing table
    op.execute("ALTER TABLE execution_reports RENAME TO execution_reports_old")

    # 2. Create partitioned table with same schema
    op.execute("""
        CREATE TABLE execution_reports (
            id BIGSERIAL,
            tool_id UUID NOT NULL,
            success BOOLEAN NOT NULL,
            error_category VARCHAR(128),
            latency_ms INTEGER,
            context_hash VARCHAR(64) DEFAULT '__global__',
            reporter_fingerprint VARCHAR(64),
            data_pool VARCHAR(128),
            session_id VARCHAR(64),
            attempt_number INTEGER,
            previous_tool VARCHAR(512),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
    """)

    # 3. Create a default partition to catch any rows outside defined ranges
    op.execute("""
        CREATE TABLE execution_reports_default
        PARTITION OF execution_reports DEFAULT
    """)

    # 4. Create partitions for existing data range + a few months ahead
    # Find the date range of existing data and create monthly partitions
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT MIN(created_at), MAX(created_at) FROM execution_reports_old"
    ))
    row = result.fetchone()
    min_date, max_date = row[0], row[1]

    if min_date is not None:
        # Create partitions from min_date month through 3 months after max_date
        current = datetime(min_date.year, min_date.month, 1)
        end = datetime(max_date.year, max_date.month + 4, 1) if max_date.month <= 9 else datetime(max_date.year + 1, (max_date.month + 4 - 1) % 12 + 1, 1)

        while current < end:
            if current.month == 12:
                next_month = datetime(current.year + 1, 1, 1)
            else:
                next_month = datetime(current.year, current.month + 1, 1)

            name = f"execution_reports_y{current.year}m{current.month:02d}"
            op.execute(f"""
                CREATE TABLE "{name}"
                PARTITION OF execution_reports
                FOR VALUES FROM ('{current.isoformat()}') TO ('{next_month.isoformat()}')
            """)
            current = next_month

    # 5. Copy data from old table
    op.execute("""
        INSERT INTO execution_reports (
            id, tool_id, success, error_category, latency_ms, context_hash,
            reporter_fingerprint, data_pool, session_id, attempt_number,
            previous_tool, created_at
        )
        SELECT id, tool_id, success, error_category, latency_ms, context_hash,
               reporter_fingerprint, data_pool, session_id, attempt_number,
               previous_tool, created_at
        FROM execution_reports_old
    """)

    # 6. Recreate indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_reports_tool_created ON execution_reports (tool_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reports_session ON execution_reports (session_id) WHERE session_id IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reports_created ON execution_reports (created_at DESC)")

    # 7. Re-add foreign key
    op.execute("""
        ALTER TABLE execution_reports
        ADD CONSTRAINT fk_reports_tool FOREIGN KEY (tool_id) REFERENCES tools(id)
    """)

    # 8. Reset sequence
    op.execute("SELECT setval('execution_reports_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM execution_reports_old))")

    # 9. Drop old table
    op.execute("DROP TABLE execution_reports_old")


def downgrade() -> None:
    # Convert back to regular table
    op.execute("ALTER TABLE execution_reports RENAME TO execution_reports_partitioned")

    op.execute("""
        CREATE TABLE execution_reports (
            id BIGSERIAL PRIMARY KEY,
            tool_id UUID NOT NULL REFERENCES tools(id),
            success BOOLEAN NOT NULL,
            error_category VARCHAR(128),
            latency_ms INTEGER,
            context_hash VARCHAR(64) DEFAULT '__global__',
            reporter_fingerprint VARCHAR(64),
            data_pool VARCHAR(128),
            session_id VARCHAR(64),
            attempt_number INTEGER,
            previous_tool VARCHAR(512),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        INSERT INTO execution_reports
        SELECT * FROM execution_reports_partitioned
    """)

    op.execute("DROP TABLE execution_reports_partitioned CASCADE")
    op.execute("CREATE INDEX idx_reports_tool_created ON execution_reports (tool_id, created_at DESC)")
    op.execute("CREATE INDEX idx_reports_session ON execution_reports (session_id)")
    op.execute("CREATE INDEX idx_reports_created ON execution_reports (created_at DESC)")
