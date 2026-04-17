"""normalize legacy webhook tool_identifier values to their canonical form

Revision ID: o5j6k7l8mno
Revises: n4i5j6k7lmn
Create Date: 2026-04-17 11:05:00.000000

The ``POST /v1/webhooks`` handler stored ``body.tool_identifier`` verbatim
before the companion code fix, while ``report_ingest.dispatch_score_change``
(which filters webhooks at delivery time) was keyed on ``Tool.identifier``
— always the canonical, normalized form. Net effect: any webhook
registered with a mixed-case host or a trailing slash was silently dead,
because its stored filter value never matched the canonical key the
dispatcher looked up.

The code fix (same commit as this migration) normalizes on registration
so every *new* webhook stores the canonical form. This migration applies
the same ``normalize_identifier`` pass to rows that already exist, so
legacy webhooks start firing on the next score change without the owner
having to re-register.

No unique constraint exists on ``webhooks.tool_identifier`` (one account
can register many webhooks for the same tool under different thresholds),
so the UPDATE is safe without conflict handling.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# Importing from the app package is fine here — alembic runs from the
# project root and the migration is tied to this codebase's
# identifier-normalization rules. Keeping the logic in one place avoids
# a divergence between the runtime normalizer and a reimplemented-in-SQL
# stand-in.
from app.core.identifiers import normalize_identifier


revision: str = "o5j6k7l8mno"
down_revision: Union[str, Sequence[str], None] = "n4i5j6k7lmn"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, tool_identifier FROM webhooks "
            "WHERE tool_identifier IS NOT NULL"
        )
    ).fetchall()

    for row_id, raw in rows:
        canonical = normalize_identifier(raw)
        if canonical == raw:
            continue  # Already canonical, skip the UPDATE round-trip.
        bind.execute(
            sa.text(
                "UPDATE webhooks SET tool_identifier = :canonical "
                "WHERE id = :id"
            ),
            {"canonical": canonical, "id": row_id},
        )


def downgrade() -> None:
    # Intentionally a no-op. ``normalize_identifier`` is a lossy fold —
    # mixed-case hosts collapse to lowercase, trailing slashes drop —
    # and the pre-canonicalisation form is not recoverable from the row
    # alone. A downgrade would have to restore from backup.
    pass
