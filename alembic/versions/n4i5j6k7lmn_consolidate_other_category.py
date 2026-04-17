"""consolidate legacy "Other" category into "Other APIs"

Revision ID: n4i5j6k7lmn
Revises: m3h4i5j6klm
Create Date: 2026-04-17 11:00:00.000000

Before this migration the canonical taxonomy carried two "I don't know"
buckets:

* ``normalize_category`` fell back to ``"Other APIs"`` for any unfamiliar
  input and for the LLM/import paths that default to it.
* The alias map steered ``"other"`` / ``"misc"`` / ``"miscellaneous"`` /
  ``"unknown"`` to ``"Other"``.

So every unknown tool split into two buckets depending on whether the
source was an alias or a genuinely unfamiliar category string —
fragmenting ``?category=other`` filters, analytics groupings, and the
admin dashboard breakdown.

The application-side fix (commit to follow) removes ``"Other"`` from
``CANONICAL_CATEGORIES`` and points every alias at ``"Other APIs"``.
This migration is the data-side half: rename every pre-existing
``Tool.category == "Other"`` row so the ``/v1/tools?category=other``
filter (which now normalizes to ``"Other APIs"``) matches them.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "n4i5j6k7lmn"
down_revision: Union[str, Sequence[str], None] = "m3h4i5j6klm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Case-insensitive on purpose. Prior writers included the LLM-assessor
    # path, which has historically emitted both ``"Other"`` and the rare
    # ``"other"`` spelling depending on the model — we want both to land
    # in the canonical ``"Other APIs"`` bucket.
    op.execute(
        "UPDATE tools SET category = 'Other APIs' WHERE LOWER(category) = 'other'"
    )


def downgrade() -> None:
    # Intentionally a no-op. The pre-consolidation state had "Other" and
    # "Other APIs" as two distinct values, but we have no way to know
    # which bucket a given row originated in — every row touched by the
    # upgrade looked like "Other" before. Forcing them all back to
    # "Other" would be a guess that corrupts any "Other APIs" rows
    # written after the upgrade. A manual rollback (if ever needed)
    # would have to inspect the audit log / git blame for the tool and
    # pick the right bucket per row.
    pass
