"""Validation tests for the /v1/assess request schema.

Specifically guards the upper bounds on budget fields: without a ``le=``
cap, a caller could submit ``max_price_per_call=999999999.99`` (typo or
confused unit) and silently pass validation, producing nonsensical
``within_budget`` flags downstream.
"""

import pytest
from pydantic import ValidationError

from app.schemas.assess import AssessRequest


class TestBudgetFieldBounds:
    def test_max_price_per_call_accepts_realistic_value(self):
        body = AssessRequest(
            tool_identifier="https://api.example.com",
            max_price_per_call=0.05,
        )
        assert body.max_price_per_call == 0.05

    def test_max_price_per_call_rejects_absurd_value(self):
        with pytest.raises(ValidationError) as exc_info:
            AssessRequest(
                tool_identifier="https://api.example.com",
                max_price_per_call=10_001,
            )
        assert "max_price_per_call" in str(exc_info.value)

    def test_max_price_per_call_rejects_negative(self):
        with pytest.raises(ValidationError):
            AssessRequest(
                tool_identifier="https://api.example.com",
                max_price_per_call=-0.01,
            )

    def test_max_monthly_budget_accepts_large_enterprise_value(self):
        body = AssessRequest(
            tool_identifier="https://api.example.com",
            max_monthly_budget=1_000_000,
        )
        assert body.max_monthly_budget == 1_000_000

    def test_max_monthly_budget_rejects_absurd_value(self):
        with pytest.raises(ValidationError) as exc_info:
            AssessRequest(
                tool_identifier="https://api.example.com",
                max_monthly_budget=10_000_001,
            )
        assert "max_monthly_budget" in str(exc_info.value)
