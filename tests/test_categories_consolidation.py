"""Regression tests for the ``Other APIs`` / ``Other`` category consolidation.

Before the fix, the taxonomy had both as canonicals:

* the fallback at the bottom of ``normalize_category`` returned ``"Other APIs"``
* the alias map steered ``"other"`` / ``"misc"`` / ``"unknown"`` to ``"Other"``

So every "I don't know" tool split into two buckets depending on whether
the input was an alias or genuinely unfamiliar — fragmenting every
category-filtered query, analytics grouping, and admin breakdown.
"""
from app.core.categories import CANONICAL_CATEGORIES, normalize_category


def test_other_is_no_longer_a_standalone_canonical() -> None:
    """A second catch-all bucket would split the 'unknown tools' pile."""
    assert "Other" not in CANONICAL_CATEGORIES
    assert "Other APIs" in CANONICAL_CATEGORIES


def test_alias_targets_collapse_to_other_apis() -> None:
    """Every 'unknown' alias funnels into the single canonical bucket."""
    for raw in ("other", "misc", "miscellaneous", "unknown", "Other", "OTHER"):
        assert normalize_category(raw) == "Other APIs", f"alias {raw!r} did not fold"


def test_unfamiliar_string_falls_back_to_other_apis() -> None:
    """And so does anything we've never heard of — same bucket as the aliases."""
    assert normalize_category("something_weird_that_nobody_emits") == "Other APIs"


def test_empty_input_still_returns_none() -> None:
    """Non-empty-string remains the only trigger for the NULL column path."""
    assert normalize_category(None) is None
    assert normalize_category("") is None
    assert normalize_category("   ") is None
