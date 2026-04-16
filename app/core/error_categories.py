"""Canonical error-category constants shared by the schema, scoring, and SDKs.

Two disjoint sets:

* ``CANONICAL_ERROR_CATEGORIES`` — the 8 documented values an agent reports
  when a tool actually failed. Public API contract; mirrored verbatim in
  ``/llms-full.txt`` and in the SDK ``_classify_error`` helper.
* ``SDK_TELEMETRY_CATEGORIES`` — markers the ``guard()`` helpers emit when
  the SDK *chose* not to call a tool (score below ``min_score`` or over
  budget). They flow through ``/v1/report`` so the journey is captured for
  fallback-chain analytics, but they are **not** tool failures and must
  NOT count toward the reliability score, the failure-rate trend, the
  pitfall stats, or the latency percentiles.

The schema validates ``error_category`` against the union so unknown strings
(typos, drive-by junk) get a clean 422 instead of silently polluting the
pitfall histogram. The skip markers stay in the union so older SDKs in the
wild keep working — the scoring layer is the one that filters them out.
"""

from typing import Literal


CANONICAL_ERROR_CATEGORIES: tuple[str, ...] = (
    "timeout",
    "rate_limit",
    "auth_failure",
    "validation_error",
    "server_error",
    "connection_error",
    "not_found",
    "permission_denied",
)

SDK_TELEMETRY_CATEGORIES: tuple[str, ...] = (
    "skipped_low_score",
    "skipped_over_budget",
)

ALL_ERROR_CATEGORIES: tuple[str, ...] = (
    *CANONICAL_ERROR_CATEGORIES,
    *SDK_TELEMETRY_CATEGORIES,
)

# Literal mirror of ALL_ERROR_CATEGORIES for type-checking + Pydantic.
# Keep this in lockstep with the tuple above — Python has no DRY way to
# generate a Literal from a runtime sequence.
ErrorCategory = Literal[
    "timeout",
    "rate_limit",
    "auth_failure",
    "validation_error",
    "server_error",
    "connection_error",
    "not_found",
    "permission_denied",
    "skipped_low_score",
    "skipped_over_budget",
]


def is_sdk_skip(category: str | None) -> bool:
    """True when the category is an SDK skip marker, not a real tool failure."""
    return category in SDK_TELEMETRY_CATEGORIES
