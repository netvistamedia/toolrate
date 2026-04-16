"""dedupe + lookup index on (fingerprint, session_id, attempt_number)

Revision ID: m3h4i5j6klm
Revises: l2g3h4i5jkl
Create Date: 2026-04-16 12:30:00.000000

Concurrent ``/v1/report`` calls for the same ``session_id`` + ``attempt_number``
under a single reporter fingerprint can both insert before either commits,
leaving duplicate rows that double-count the journey in the fallback-chain
analytics.

We can't enforce the constraint with a Postgres UNIQUE INDEX because
``execution_reports`` is partitioned on ``created_at`` and Postgres
requires unique indexes on partitioned tables to include every partition
key column — adding ``created_at`` would defeat the purpose (every
concurrent insert gets a different timestamp). So this migration just
adds a *non-unique* lookup index so the app-layer dedup check
(``ingest_report`` does a fast SELECT before INSERT) stays cheap, and
deduplicates the legacy rows that already exist.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "m3h4i5j6klm"
down_revision: Union[str, Sequence[str], None] = "l2g3h4i5jkl"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Dedupe legacy rows so the post-migration data matches the post-fix
    # invariant (one row per fingerprint+session+attempt). Keep the oldest
    # row (smallest id) per group; drop the rest. Skips NULL groups since
    # those are reports without journey metadata and are not deduplicated.
    op.execute(
        """
        DELETE FROM execution_reports
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY reporter_fingerprint, session_id, attempt_number
                           ORDER BY id
                       ) AS rn
                FROM execution_reports
                WHERE session_id IS NOT NULL
                  AND attempt_number IS NOT NULL
            ) ranked
            WHERE ranked.rn > 1
        )
        """
    )

    op.create_index(
        "idx_reports_fingerprint_session_attempt",
        "execution_reports",
        ["reporter_fingerprint", "session_id", "attempt_number"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_reports_fingerprint_session_attempt", "execution_reports"
    )
