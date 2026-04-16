"""dedupe + unique index on (fingerprint, session_id, attempt_number)

Revision ID: m3h4i5j6klm
Revises: l2g3h4i5jkl
Create Date: 2026-04-16 12:30:00.000000

Concurrent ``/v1/report`` calls for the same ``session_id`` + ``attempt_number``
under a single reporter fingerprint can both insert before either commits,
leaving duplicate rows that double-count the journey in the fallback-chain
analytics. The unique index enforces "one report per attempt within a
session" going forward; the dedupe step keeps existing data clean.

Both Postgres and SQLite treat NULL as distinct in unique indexes, so
legacy reports that never carried journey metadata (both columns NULL)
remain unaffected.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "m3h4i5j6klm"
down_revision: Union[str, Sequence[str], None] = "l2g3h4i5jkl"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Dedupe BEFORE adding the unique index — otherwise the index creation
    # would fail on any existing duplicate rows. Keep the row with the
    # smallest id (oldest insert) for each (fingerprint, session, attempt)
    # group; drop the rest. Skips groups where any column is NULL since
    # those are excluded from the constraint anyway.
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
        "uq_reports_fingerprint_session_attempt",
        "execution_reports",
        ["reporter_fingerprint", "session_id", "attempt_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_reports_fingerprint_session_attempt", "execution_reports"
    )
