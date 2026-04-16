"""Validation tests for the /v1/report request schema.

The error_category field used to accept arbitrary strings (max_length=128),
which let typos and drive-by junk like ``"timed_out"`` or ``"oops"`` slip
into the pitfall stats. The Literal type restricts inputs to the documented
8 canonical categories plus the 2 SDK telemetry markers.
"""

import pytest
from pydantic import ValidationError

from app.core.error_categories import (
    CANONICAL_ERROR_CATEGORIES,
    SDK_TELEMETRY_CATEGORIES,
    is_sdk_skip,
)
from app.schemas.report import ReportRequest


class TestErrorCategoryValidation:
    @pytest.mark.parametrize("category", list(CANONICAL_ERROR_CATEGORIES))
    def test_canonical_categories_accepted(self, category):
        body = ReportRequest(
            tool_identifier="https://api.example.com",
            success=False,
            error_category=category,
        )
        assert body.error_category == category

    @pytest.mark.parametrize("category", list(SDK_TELEMETRY_CATEGORIES))
    def test_sdk_skip_markers_accepted(self, category):
        body = ReportRequest(
            tool_identifier="https://api.example.com",
            success=False,
            error_category=category,
        )
        assert body.error_category == category

    def test_none_accepted_for_unlabeled_failure(self):
        body = ReportRequest(
            tool_identifier="https://api.example.com",
            success=False,
            error_category=None,
        )
        assert body.error_category is None

    def test_unknown_category_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ReportRequest(
                tool_identifier="https://api.example.com",
                success=False,
                error_category="timed_out",  # close to canonical but not in the set
            )
        # Pydantic's error message must mention the field so the developer
        # knows what to fix without diving into the schema.
        assert "error_category" in str(exc_info.value)

    def test_arbitrary_string_rejected(self):
        with pytest.raises(ValidationError):
            ReportRequest(
                tool_identifier="https://api.example.com",
                success=False,
                error_category="something the agent made up",
            )


class TestSdkSkipHelper:
    @pytest.mark.parametrize("category", list(SDK_TELEMETRY_CATEGORIES))
    def test_skip_markers_classified_as_skip(self, category):
        assert is_sdk_skip(category) is True

    @pytest.mark.parametrize("category", list(CANONICAL_ERROR_CATEGORIES))
    def test_canonical_categories_not_classified_as_skip(self, category):
        assert is_sdk_skip(category) is False

    def test_none_not_classified_as_skip(self):
        # Unlabeled failures are still failures; only the explicit SDK markers
        # are excluded from the reliability calculation.
        assert is_sdk_skip(None) is False
