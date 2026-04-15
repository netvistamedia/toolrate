"""Tests for cost-aware scoring — the helpers in app/services/scoring.py
plus the end-to-end ``finalize_response`` flow that wires them together.

Unit tests (no DB) cover the pure helpers so the math is locked down without
needing a running engine. The integration section uses the same SQLite
fixture pattern as ``test_scoring.py`` to verify the DB-backed median lookup
and the full compute_score → finalize_response pipeline.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base
from app.models.tool import Tool
from app.models.tool_pricing_history import ToolPricingHistory
from app.schemas.assess import AlternativeTool, AssessResponse
from app.services.scoring import (
    _STRATEGY_WEIGHTS,
    _CATEGORY_MEDIAN_CACHE,
    _CATEGORY_LATENCY_MEDIAN_CACHE,
    _annotate_alternatives_within_budget,
    _apply_cost_adjustment,
    _budget_explanation,
    _build_reasoning,
    _category_median_cost,
    _category_median_latency_ms,
    _cost_adjusted_score,
    _effective_cost,
    _is_within_budget,
    _per_call_cost_for_tokens,
    _pick_recommended_model,
    _tool_latency_ms,
    compute_score,
    finalize_response,
)


TEST_DATABASE_URL = "sqlite+aiosqlite:///test_cost_scoring.db"


# ──────────────────────────────────────────────────────────────────────────
# Unit tests — pure functions, no DB
# ──────────────────────────────────────────────────────────────────────────


class TestEffectiveCost:
    def test_none_pricing_returns_none(self):
        assert _effective_cost(None, None) is None
        assert _effective_cost({}, None) is None

    def test_base_price_preferred_over_typical(self):
        pricing = {"base_usd_per_call": 0.01, "typical_usd_per_call": 0.99}
        assert _effective_cost(pricing, None) == 0.01

    def test_typical_used_when_base_is_null(self):
        pricing = {"base_usd_per_call": None, "typical_usd_per_call": 0.02}
        assert _effective_cost(pricing, None) == 0.02

    def test_returns_none_when_both_prices_null(self):
        pricing = {"base_usd_per_call": None, "typical_usd_per_call": None}
        assert _effective_cost(pricing, None) is None

    def test_free_tier_below_expected_amortizes(self):
        # 3000 free + $0.001 each for the remaining 2000 calls out of 5000
        # → effective = (2000 * 0.001) / 5000 = $0.0004
        pricing = {"base_usd_per_call": 0.001, "free_tier_per_month": 3000}
        assert _effective_cost(pricing, 5000) == pytest.approx(0.0004, abs=1e-9)

    def test_free_tier_above_expected_is_zero(self):
        # 5000 free, only using 2000 → 100% covered by free tier
        pricing = {"base_usd_per_call": 0.001, "free_tier_per_month": 5000}
        assert _effective_cost(pricing, 2000) == 0.0

    def test_free_tier_ignored_when_no_expected_volume(self):
        pricing = {"base_usd_per_call": 0.001, "free_tier_per_month": 5000}
        assert _effective_cost(pricing, None) == 0.001

    def test_negative_raw_price_clamped_to_zero(self):
        pricing = {"base_usd_per_call": -0.01}
        assert _effective_cost(pricing, None) == 0.0

    def test_expected_tokens_prefers_per_million_math(self):
        # 1000 tokens at 30/70 split = 300 in + 700 out
        # 300 * $3/M + 700 * $15/M = $0.0009 + $0.0105 = $0.0114
        pricing = {
            "usd_per_million_input_tokens": 3.0,
            "usd_per_million_output_tokens": 15.0,
            "typical_usd_per_call": 0.999,  # intentionally wrong to prove we pick per-token
        }
        assert _effective_cost(pricing, None, expected_tokens=1000) == pytest.approx(0.0114, rel=1e-6)

    def test_expected_tokens_falls_back_when_per_million_missing(self):
        # No per-M pricing → fall through to typical_usd_per_call
        pricing = {"typical_usd_per_call": 0.005}
        assert _effective_cost(pricing, None, expected_tokens=1000) == 0.005

    def test_expected_tokens_zero_falls_back_to_blend(self):
        # zero or None tokens = blend math
        pricing = {
            "usd_per_million_input_tokens": 3.0,
            "usd_per_million_output_tokens": 15.0,
            "typical_usd_per_call": 0.02,
        }
        assert _effective_cost(pricing, None, expected_tokens=0) == 0.02
        assert _effective_cost(pricing, None, expected_tokens=None) == 0.02


class TestPerCallCostForTokens:
    def test_returns_none_without_expected_tokens(self):
        pricing = {
            "usd_per_million_input_tokens": 3.0,
            "usd_per_million_output_tokens": 15.0,
        }
        assert _per_call_cost_for_tokens(pricing, None) is None
        assert _per_call_cost_for_tokens(pricing, 0) is None

    def test_returns_none_without_per_million_fields(self):
        assert _per_call_cost_for_tokens({}, 1000) is None
        assert _per_call_cost_for_tokens(
            {"usd_per_million_input_tokens": 3.0}, 1000
        ) is None

    def test_30_70_split_matches_hand_computed(self):
        # 1000 tokens: 300 in * 2.50/M + 700 out * 10/M
        # = 0.00075 + 0.00700 = 0.00775
        pricing = {
            "usd_per_million_input_tokens": 2.50,
            "usd_per_million_output_tokens": 10.00,
        }
        assert _per_call_cost_for_tokens(pricing, 1000) == pytest.approx(0.00775, rel=1e-6)

    def test_groq_cheap_model_rounds_to_micropennies(self):
        # Groq 8B: $0.05/M in, $0.08/M out — 1000 tokens ≈ $0.000071
        pricing = {
            "usd_per_million_input_tokens": 0.05,
            "usd_per_million_output_tokens": 0.08,
        }
        cost = _per_call_cost_for_tokens(pricing, 1000)
        assert cost == pytest.approx(0.000071, rel=1e-3)

    def test_custom_input_ratio(self):
        # 50/50 split: 500 in + 500 out at $1/M/$1/M = $0.001
        pricing = {
            "usd_per_million_input_tokens": 1.0,
            "usd_per_million_output_tokens": 1.0,
        }
        assert _per_call_cost_for_tokens(pricing, 1000, input_ratio=0.5) == pytest.approx(0.001, rel=1e-6)

    def test_negative_price_clamped(self):
        pricing = {
            "usd_per_million_input_tokens": -5.0,
            "usd_per_million_output_tokens": 10.0,
        }
        # input is clamped to 0, only output contributes
        # 700 out * $10/M = $0.007
        assert _per_call_cost_for_tokens(pricing, 1000) == pytest.approx(0.007, rel=1e-6)


class TestCostAdjustedScore:
    def test_strategy_weights_sum_to_one(self):
        # All four strategies are 3-tuples (reliability, cost, latency) and
        # must sum to exactly 1.0 so the score math scales 0-100 cleanly.
        for strategy, weights in _STRATEGY_WEIGHTS.items():
            assert len(weights) == 3, strategy
            assert sum(weights) == pytest.approx(1.0), strategy

    def test_preserved_two_axis_strategy_weights(self):
        # The three legacy strategies were locked in on 2026-04-15 — they
        # must not drift. speed_first is new; the other three stay pinned.
        assert _STRATEGY_WEIGHTS["reliability_first"] == (0.80, 0.20, 0.00)
        assert _STRATEGY_WEIGHTS["balanced"] == (0.55, 0.45, 0.00)
        assert _STRATEGY_WEIGHTS["cost_first"] == (0.25, 0.75, 0.00)

    def test_speed_first_weights(self):
        assert _STRATEGY_WEIGHTS["speed_first"] == (0.35, 0.45, 0.20)

    def test_free_tool_gets_full_cost_bonus(self):
        # reliability=90, cost=0, median=0.01 → cost_norm=0, cost side = 100
        # reliability_first: 0.80 * 90 + 0.20 * 100 = 72 + 20 = 92
        assert _cost_adjusted_score(90.0, 0.0, 0.01, "reliability_first") == 92.0

    def test_at_median_gets_half_cost_bonus(self):
        # cost_norm = 1.0 → cost side = 0
        # balanced: 0.55 * 80 + 0.45 * 0 = 44
        assert _cost_adjusted_score(80.0, 0.01, 0.01, "balanced") == 44.0

    def test_cost_first_penalizes_expensive_tools_hard(self):
        # Expensive tool (2x median), reliability=95
        # cost_norm=min(1, 2)=1 → cost side = 0
        # cost_first: 0.25 * 95 + 0.75 * 0 = 23.75 → 23.8
        assert _cost_adjusted_score(95.0, 0.02, 0.01, "cost_first") == 23.8

    def test_unknown_strategy_falls_back_to_reliability_first(self):
        a = _cost_adjusted_score(90.0, 0.005, 0.01, "nonsense_strategy")
        b = _cost_adjusted_score(90.0, 0.005, 0.01, "reliability_first")
        assert a == b

    def test_no_median_all_free_no_penalty(self):
        # peer group is all-free and so is this tool
        assert _cost_adjusted_score(90.0, 0.0, None, "reliability_first") == 92.0

    def test_no_median_paid_tool_full_penalty(self):
        # peer group is all-free but this tool costs → full cost penalty
        # 0.80 * 90 + 0.20 * 0 = 72
        assert _cost_adjusted_score(90.0, 0.01, None, "reliability_first") == 72.0

    def test_speed_first_without_latency_data_degrades_gracefully(self):
        # No latency signal → fold 0.20 latency weight into reliability
        # so the score stays meaningful. 0.55 * 90 + 0.45 * 50 = 72.0
        score = _cost_adjusted_score(
            90.0, 0.005, 0.01, "speed_first",
            latency_ms=None, category_median_latency_ms=None,
        )
        # reliability effective weight = 0.35 + 0.20 = 0.55
        # 0.55 * 90 + 0.45 * 50 + 0.0 * 0 = 49.5 + 22.5 = 72.0
        assert score == 72.0

    def test_speed_first_with_latency_at_median(self):
        # latency == median → lat_norm = 1.0 → lat_side = 0
        # 0.35 * 90 + 0.45 * 50 + 0.20 * 0 = 31.5 + 22.5 + 0 = 54.0
        score = _cost_adjusted_score(
            90.0, 0.005, 0.01, "speed_first",
            latency_ms=1000.0, category_median_latency_ms=1000.0,
        )
        assert score == 54.0

    def test_speed_first_rewards_fast_tool(self):
        # latency at half the median → lat_norm = 0.5 → lat_side = 50
        # 0.35 * 90 + 0.45 * 50 + 0.20 * 50 = 31.5 + 22.5 + 10.0 = 64.0
        score = _cost_adjusted_score(
            90.0, 0.005, 0.01, "speed_first",
            latency_ms=500.0, category_median_latency_ms=1000.0,
        )
        assert score == 64.0

    def test_speed_first_caps_slow_tool_at_full_latency_penalty(self):
        # latency at 10x median → clamped to 1.0 → lat_side = 0
        # identical to at-median case: 54.0
        score = _cost_adjusted_score(
            90.0, 0.005, 0.01, "speed_first",
            latency_ms=10000.0, category_median_latency_ms=1000.0,
        )
        assert score == 54.0


class TestIsWithinBudget:
    def test_no_caps_always_within(self):
        assert _is_within_budget(0.99, None, None, None) is True

    def test_below_per_call_cap(self):
        assert _is_within_budget(0.01, 0.03, None, None) is True

    def test_above_per_call_cap(self):
        assert _is_within_budget(0.05, 0.03, None, None) is False

    def test_monthly_cap_respected_only_with_expected_calls(self):
        # Without expected volume we cannot project monthly spend, so the
        # monthly cap is ignored (per-call still applies if set).
        assert _is_within_budget(0.01, None, 10.0, None) is True

    def test_monthly_cap_below_triggers_false(self):
        # 1000 calls * $0.01 = $10.00 > $5 cap
        assert _is_within_budget(0.01, None, 5.0, 1000) is False

    def test_monthly_cap_above_fits(self):
        assert _is_within_budget(0.01, None, 100.0, 1000) is True

    def test_both_caps_must_pass(self):
        # Per-call $0.01 fits per-call cap ($0.02), but monthly $20 exceeds $10
        assert _is_within_budget(0.01, 0.02, 10.0, 2000) is False


class TestBudgetExplanation:
    def _make_tool(self, name="Stripe"):
        return Tool(
            id=uuid.uuid4(),
            identifier="https://api.stripe.com/v1/charges",
            display_name=name,
        )

    def test_fits_within_per_call_cap(self):
        msg = _budget_explanation(
            self._make_tool(), 0.01, max_price_per_call=0.05,
            max_monthly_budget=None, expected_calls_per_month=None,
            within_budget=True,
        )
        assert "Stripe" in msg
        assert "fits" in msg.lower()
        assert "0.0100" in msg
        assert "0.0500" in msg

    def test_over_per_call_mentions_overage(self):
        msg = _budget_explanation(
            self._make_tool(), 0.10, max_price_per_call=0.03,
            max_monthly_budget=None, expected_calls_per_month=None,
            within_budget=False,
        )
        assert "exceeds" in msg
        assert "0.1000" in msg
        assert "0.0300" in msg
        assert "0.0700" in msg  # overage

    def test_over_monthly_mentions_projected_spend(self):
        msg = _budget_explanation(
            self._make_tool(), 0.01, max_price_per_call=None,
            max_monthly_budget=5.0, expected_calls_per_month=1000,
            within_budget=False,
        )
        assert "10.00" in msg  # 1000 * 0.01
        assert "5.00" in msg
        assert "exceeds" in msg

    def test_uses_identifier_when_display_name_missing(self):
        tool = Tool(
            id=uuid.uuid4(),
            identifier="https://example.com/api",
            display_name=None,
        )
        msg = _budget_explanation(
            tool, 0.01, max_price_per_call=0.05,
            max_monthly_budget=None, expected_calls_per_month=None,
            within_budget=True,
        )
        assert "https://example.com/api" in msg


class TestApplyCostAdjustment:
    def _make_response(self, reliability: float = 90.0) -> AssessResponse:
        return AssessResponse(
            reliability_score=reliability,
            confidence=0.8,
            data_source="empirical",
            historical_success_rate="90%",
            predicted_failure_risk="low",
            trend=None,
            common_pitfalls=[],
            recommended_mitigations=[],
            top_alternatives=[],
            estimated_latency_ms=None,
            latency=None,
            last_updated=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
        )

    def _make_tool(self, pricing: dict | None) -> Tool:
        return Tool(
            id=uuid.uuid4(),
            identifier="https://api.example.com/v1",
            display_name="Example",
            category="test",
            pricing=pricing,
        )

    def _apply(self, resp, tool, **kwargs):
        """Thin wrapper that fills in the new task_complexity + expected_tokens
        + category_median_latency_ms kwargs so individual tests stay focused
        on whatever they care about. Kwargs override the defaults."""
        base = dict(
            max_price_per_call=None,
            max_monthly_budget=None,
            expected_calls_per_month=None,
            expected_tokens=None,
            task_complexity="medium",
            budget_strategy="reliability_first",
            category_median=0.01,
            category_median_latency_ms=None,
        )
        base.update(kwargs)
        _apply_cost_adjustment(resp, tool, **base)

    def test_tool_without_pricing_and_no_budget_leaves_everything_none(self):
        resp = self._make_response()
        tool = self._make_tool(None)
        self._apply(resp, tool)
        assert resp.price_per_call is None
        assert resp.pricing_model is None
        assert resp.cost_adjusted_score is None
        assert resp.within_budget is None
        assert resp.budget_explanation is None
        # reasoning is always populated now, even for pricing-less tools
        assert resp.reasoning is not None

    def test_tool_without_pricing_with_budget_explains(self):
        resp = self._make_response()
        tool = self._make_tool(None)
        self._apply(resp, tool, max_price_per_call=0.01)
        assert resp.budget_explanation == "No pricing data available for this tool."

    def test_tool_with_pricing_populates_cost_fields(self):
        resp = self._make_response(reliability=90.0)
        tool = self._make_tool({
            "model": "per_call",
            "base_usd_per_call": 0.005,
            "typical_usd_per_call": None,
        })
        self._apply(resp, tool)
        assert resp.price_per_call == 0.005
        assert resp.pricing_model == "per_call"
        # cost_norm = 0.005/0.01 = 0.5 → cost side = 50
        # reliability_first: 0.80 * 90 + 0.20 * 50 = 72 + 10 = 82
        assert resp.cost_adjusted_score == 82.0

    def test_expected_calls_drives_estimated_monthly_cost(self):
        resp = self._make_response()
        tool = self._make_tool({"model": "per_call", "base_usd_per_call": 0.001})
        self._apply(
            resp, tool,
            expected_calls_per_month=10000,
            category_median=0.001,
        )
        assert resp.estimated_monthly_cost == 10.0  # 10000 * 0.001
        assert resp.budget_explanation is not None
        assert "10.00" in resp.budget_explanation

    def test_over_budget_sets_within_budget_false_and_flag(self):
        resp = self._make_response()
        tool = self._make_tool({"model": "per_call", "base_usd_per_call": 0.10})
        self._apply(
            resp, tool,
            max_price_per_call=0.01,
            budget_strategy="balanced",
        )
        assert resp.within_budget is False
        assert "exceeds" in resp.budget_explanation

    def test_different_strategies_produce_different_scores(self):
        tool = self._make_tool({"model": "per_call", "base_usd_per_call": 0.02})
        scores: dict[str, float] = {}
        for strategy in ("reliability_first", "balanced", "cost_first"):
            resp = self._make_response(reliability=90.0)
            self._apply(resp, tool, budget_strategy=strategy)
            scores[strategy] = resp.cost_adjusted_score

        # Expensive tool (2x median) should score worst under cost_first
        # and best under reliability_first.
        assert scores["reliability_first"] > scores["balanced"]
        assert scores["balanced"] > scores["cost_first"]

    def test_reasoning_populated_on_priced_tool(self):
        resp = self._make_response(reliability=95.0)
        tool = self._make_tool({
            "model": "per_token",
            "typical_usd_per_call": 0.01,
            "recommended_model": "claude-sonnet-4-6",
        })
        self._apply(resp, tool, budget_strategy="reliability_first")
        assert resp.reasoning is not None
        assert "reliability-first" in resp.reasoning
        assert "claude-sonnet-4-6" in resp.reasoning
        assert resp.recommended_model == "claude-sonnet-4-6"


class TestAnnotateAlternativesWithinBudget:
    def test_no_cap_no_mutation(self):
        alts = [
            AlternativeTool(tool="a", score=90.0, reason="x", price_per_call=0.05),
            AlternativeTool(tool="b", score=80.0, reason="y", price_per_call=0.10),
        ]
        _annotate_alternatives_within_budget(alts, None, None, None)
        assert all(a.within_budget is None for a in alts)

    def test_flags_over_and_under(self):
        alts = [
            AlternativeTool(tool="cheap", score=90.0, reason="x", price_per_call=0.005),
            AlternativeTool(tool="pricey", score=95.0, reason="y", price_per_call=0.05),
            AlternativeTool(tool="unknown", score=85.0, reason="z", price_per_call=None),
        ]
        _annotate_alternatives_within_budget(alts, 0.01, None, None)
        assert alts[0].within_budget is True
        assert alts[1].within_budget is False
        assert alts[2].within_budget is None  # pricing unknown


class TestToolLatencyMs:
    def test_none_and_empty(self):
        assert _tool_latency_ms(None) is None
        assert _tool_latency_ms({}) is None

    def test_top_level_value_wins(self):
        pricing = {"typical_latency_ms": 1200, "models": [
            {"typical_latency_ms": 50},
        ]}
        assert _tool_latency_ms(pricing) == 1200.0

    def test_catalog_median_fallback(self):
        pricing = {"models": [
            {"typical_latency_ms": 500},
            {"typical_latency_ms": 1200},
            {"typical_latency_ms": 2500},
        ]}
        assert _tool_latency_ms(pricing) == 1200.0

    def test_catalog_median_even_count(self):
        pricing = {"models": [
            {"typical_latency_ms": 500},
            {"typical_latency_ms": 1500},
        ]}
        assert _tool_latency_ms(pricing) == 1000.0

    def test_catalog_without_latency_returns_none(self):
        pricing = {"models": [{"name": "foo"}, {"name": "bar"}]}
        assert _tool_latency_ms(pricing) is None


class TestPickRecommendedModel:
    _CATALOG = {
        "recommended_model": "fallback-hint",
        "models": [
            {
                "name": "tiny",
                "tier": "low",
                "usd_per_million_input_tokens": 0.10,
                "usd_per_million_output_tokens": 0.20,
                "typical_latency_ms": 200,
            },
            {
                "name": "medium",
                "tier": "medium",
                "usd_per_million_input_tokens": 1.00,
                "usd_per_million_output_tokens": 3.00,
                "typical_latency_ms": 800,
            },
            {
                "name": "big",
                "tier": "very_high",
                "usd_per_million_input_tokens": 15.00,
                "usd_per_million_output_tokens": 75.00,
                "typical_latency_ms": 3000,
            },
        ],
    }

    def test_returns_none_for_empty_pricing(self):
        name, entry = _pick_recommended_model(None, "medium", "balanced")
        assert name is None
        assert entry is None

    def test_string_hint_fallback_when_no_catalog(self):
        name, entry = _pick_recommended_model(
            {"recommended_model": "claude-sonnet-4-6"}, "medium", "balanced"
        )
        assert name == "claude-sonnet-4-6"
        assert entry is None

    def test_cost_first_picks_cheapest_capable(self):
        # task=low → all three capable → cheapest = tiny
        name, entry = _pick_recommended_model(self._CATALOG, "low", "cost_first")
        assert name == "tiny"
        assert entry is not None and entry["tier"] == "low"

    def test_cost_first_filters_incapable_models(self):
        # task=high → only "big" qualifies (very_high rank=3 ≥ 2)
        name, _ = _pick_recommended_model(self._CATALOG, "high", "cost_first")
        assert name == "big"

    def test_speed_first_picks_lowest_latency_capable(self):
        # task=medium → medium + big qualify; medium has 800ms < big's 3000ms
        name, _ = _pick_recommended_model(self._CATALOG, "medium", "speed_first")
        assert name == "medium"

    def test_reliability_first_hedges_toward_most_capable(self):
        # task=low → all capable → reliability_first picks highest tier = big
        name, _ = _pick_recommended_model(self._CATALOG, "low", "reliability_first")
        assert name == "big"

    def test_balanced_prefers_middle_ground(self):
        # task=low → all capable → balanced penalizes cost + latency,
        # rewards tier → medium wins over tiny (slightly pricier but
        # stronger) and over big (dramatically pricier).
        name, _ = _pick_recommended_model(self._CATALOG, "low", "balanced")
        assert name in ("tiny", "medium")  # both are reasonable; medium is the expected pick

    def test_very_high_complexity_returns_top_tier(self):
        name, _ = _pick_recommended_model(self._CATALOG, "very_high", "cost_first")
        assert name == "big"

    def test_no_capable_model_widens_pool(self):
        # Catalog of only "low" tier models, asking for very_high → widen.
        pricing = {
            "models": [
                {"name": "only-low", "tier": "low", "usd_per_million_input_tokens": 0.1, "usd_per_million_output_tokens": 0.2},
            ],
        }
        name, _ = _pick_recommended_model(pricing, "very_high", "cost_first")
        assert name == "only-low"


class TestBuildReasoning:
    def _make_response(self, **overrides) -> AssessResponse:
        base = dict(
            reliability_score=92.5,
            confidence=0.85,
            data_source="empirical",
            historical_success_rate="92% (last 30 days, 1500 calls)",
            predicted_failure_risk="low",
            trend=None,
            common_pitfalls=[],
            recommended_mitigations=[],
            top_alternatives=[],
            estimated_latency_ms=None,
            latency=None,
            last_updated=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
        )
        base.update(overrides)
        return AssessResponse(**base)

    def test_includes_score_and_risk(self):
        resp = self._make_response()
        msg = _build_reasoning(
            None, resp,
            task_complexity="medium",
            budget_strategy="balanced",
            recommended_model=None,
            within_budget=None,
            latency_ms=None,
        )
        assert "92.5/100" in msg
        assert "low risk" in msg
        assert "balanced" in msg
        assert "medium" in msg

    def test_uses_display_name_over_identifier(self):
        tool = Tool(
            id=uuid.uuid4(),
            identifier="https://api.anthropic.com/v1/messages",
            display_name="Anthropic Messages",
        )
        resp = self._make_response()
        msg = _build_reasoning(
            tool, resp,
            task_complexity="high",
            budget_strategy="reliability_first",
            recommended_model="claude-sonnet-4-6",
            within_budget=True,
            latency_ms=1200,
        )
        assert "Anthropic Messages" in msg
        assert "claude-sonnet-4-6" in msg
        assert "~1200ms" in msg
        assert "Fits within your budget" in msg

    def test_over_budget_flagged(self):
        resp = self._make_response(price_per_call=0.10)
        msg = _build_reasoning(
            None, resp,
            task_complexity="medium",
            budget_strategy="cost_first",
            recommended_model=None,
            within_budget=False,
            latency_ms=None,
        )
        assert "Over budget" in msg

    def test_includes_cost_and_projection(self):
        resp = self._make_response(
            price_per_call=0.0075,
            estimated_monthly_cost=75.0,
        )
        msg = _build_reasoning(
            None, resp,
            task_complexity="medium",
            budget_strategy="balanced",
            recommended_model=None,
            within_budget=True,
            latency_ms=None,
        )
        assert "$0.0075/call" in msg
        assert "$75.00/mo projected" in msg


# ──────────────────────────────────────────────────────────────────────────
# Integration tests — DB-backed median lookup + end-to-end finalize_response
# ──────────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    # Both median caches are process-global — each test expects fresh state.
    _CATEGORY_MEDIAN_CACHE.clear()
    _CATEGORY_LATENCY_MEDIAN_CACHE.clear()


async def _priced_tool(db, identifier: str, category: str, base: float | None, typical: float | None = None) -> Tool:
    pricing: dict = {
        "model": "per_call" if base is not None else "per_token",
        "base_usd_per_call": base,
        "typical_usd_per_call": typical,
    }
    tool = Tool(
        id=uuid.uuid4(),
        identifier=identifier,
        display_name=identifier.split("/")[-1],
        category=category,
        pricing=pricing,
        report_count=20,
    )
    db.add(tool)
    await db.flush()
    return tool


class TestCategoryMedianCost:
    @pytest.mark.asyncio
    async def test_returns_none_for_empty_category(self, db):
        await db.commit()
        median = await _category_median_cost(db, "Nonexistent")
        assert median is None

    @pytest.mark.asyncio
    async def test_median_of_three_priced_tools(self, db):
        await _priced_tool(db, "a", "LLM APIs", 0.001)
        await _priced_tool(db, "b", "LLM APIs", 0.005)
        await _priced_tool(db, "c", "LLM APIs", 0.010)
        await db.commit()
        median = await _category_median_cost(db, "LLM APIs")
        assert median == 0.005

    @pytest.mark.asyncio
    async def test_even_peer_count_averages_middle_two(self, db):
        await _priced_tool(db, "a", "cat", 0.001)
        await _priced_tool(db, "b", "cat", 0.003)
        await _priced_tool(db, "c", "cat", 0.007)
        await _priced_tool(db, "d", "cat", 0.009)
        await db.commit()
        median = await _category_median_cost(db, "cat")
        assert median == 0.005  # (0.003 + 0.007) / 2

    @pytest.mark.asyncio
    async def test_thin_category_falls_back_to_global(self, db):
        # Category "thin" has 1 priced peer, global pool has 4
        await _priced_tool(db, "thin1", "thin", 0.50)
        await _priced_tool(db, "fat1", "fat", 0.001)
        await _priced_tool(db, "fat2", "fat", 0.003)
        await _priced_tool(db, "fat3", "fat", 0.005)
        await db.commit()
        # Global pool including "thin1" = [0.001, 0.003, 0.005, 0.50]
        # median = (0.003 + 0.005) / 2 = 0.004
        median = await _category_median_cost(db, "thin")
        assert median == pytest.approx(0.004)


class TestFinalizeResponseIntegration:
    @pytest.mark.asyncio
    async def test_finalize_populates_cost_fields_for_priced_tool(self, db):
        await _priced_tool(db, "peer1", "test", 0.001)
        await _priced_tool(db, "peer2", "test", 0.003)
        tool = await _priced_tool(db, "target", "test", 0.002)
        await db.commit()

        response = AssessResponse(
            reliability_score=90.0,
            confidence=0.8,
            data_source="empirical",
            historical_success_rate="90%",
            predicted_failure_risk="low",
            trend=None,
            common_pitfalls=[],
            recommended_mitigations=[],
            top_alternatives=[],
            estimated_latency_ms=None,
            latency=None,
            last_updated=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
        )
        await finalize_response(
            response, db, tool,
            max_price_per_call=0.005,
            max_monthly_budget=None,
            expected_calls_per_month=1000,
            budget_strategy="balanced",
        )

        assert response.price_per_call == 0.002
        assert response.pricing_model == "per_call"
        assert response.cost_adjusted_score is not None
        assert response.estimated_monthly_cost == 2.0  # 1000 * 0.002
        assert response.within_budget is True

    @pytest.mark.asyncio
    async def test_finalize_annotates_alternatives_within_budget(self, db):
        # Build alternatives with known prices, verify within_budget flag
        # is set post-finalize when a cap is given.
        tool = await _priced_tool(db, "primary", "test", 0.001)
        await db.commit()

        response = AssessResponse(
            reliability_score=90.0,
            confidence=0.8,
            data_source="empirical",
            historical_success_rate="90%",
            predicted_failure_risk="low",
            trend=None,
            common_pitfalls=[],
            recommended_mitigations=[],
            top_alternatives=[
                AlternativeTool(tool="cheap", score=88.0, reason="x", price_per_call=0.002),
                AlternativeTool(tool="expensive", score=92.0, reason="y", price_per_call=0.10),
                AlternativeTool(tool="unknown", score=85.0, reason="z", price_per_call=None),
            ],
            estimated_latency_ms=None,
            latency=None,
            last_updated=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
        )
        await finalize_response(
            response, db, tool,
            max_price_per_call=0.005,
            max_monthly_budget=None,
            expected_calls_per_month=None,
            budget_strategy="reliability_first",
        )

        alts_by_name = {a.tool: a for a in response.top_alternatives}
        assert alts_by_name["cheap"].within_budget is True
        assert alts_by_name["expensive"].within_budget is False
        assert alts_by_name["unknown"].within_budget is None

    @pytest.mark.asyncio
    async def test_compute_score_then_finalize_with_cache_miss_pattern(self, db):
        """End-to-end: compute_score builds base response, finalize adds cost."""
        from app.models.report import ExecutionReport
        from datetime import datetime, timedelta, timezone

        tool = await _priced_tool(db, "tool-with-reports", "test", 0.003)
        now = datetime.now(timezone.utc)
        for i in range(10):
            db.add(ExecutionReport(
                tool_id=tool.id, success=True, latency_ms=200,
                context_hash="__global__", reporter_fingerprint="fp",
                created_at=now - timedelta(days=i * 0.5),
            ))
        tool.report_count = 10
        # Seed enough peers so we have a real category median
        await _priced_tool(db, "peer-a", "test", 0.001)
        await _priced_tool(db, "peer-b", "test", 0.005)
        await db.commit()

        base_response = await compute_score(db, tool, "__global__")
        # compute_score itself does NOT populate the main response cost
        # fields — that's finalize_response's job.
        assert base_response.price_per_call is None
        assert base_response.cost_adjusted_score is None

        finalized = await finalize_response(
            base_response, db, tool,
            max_price_per_call=0.01,
            max_monthly_budget=None,
            expected_calls_per_month=None,
            budget_strategy="reliability_first",
        )
        assert finalized.price_per_call == 0.003
        assert finalized.cost_adjusted_score is not None
        assert finalized.within_budget is True
        assert finalized.budget_explanation is not None


class TestToolPricingHistoryModel:
    @pytest.mark.asyncio
    async def test_history_row_round_trip(self, db):
        """Smoke test that the new model persists and round-trips cleanly."""
        tool = await _priced_tool(db, "history-tool", "test", 0.001)
        history = ToolPricingHistory(
            tool_id=tool.id,
            pricing={"model": "per_call", "base_usd_per_call": 0.001},
            source="manual",
        )
        db.add(history)
        await db.commit()
        await db.refresh(history)
        assert history.id is not None
        assert history.pricing["base_usd_per_call"] == 0.001
        assert history.source == "manual"
        assert history.observed_at is not None


# Seed helper that bakes latency into the pricing JSON so the latency-median
# tests and the speed_first integration test share a single factory.
async def _priced_tool_with_latency(
    db, identifier: str, category: str, base: float, latency_ms: int,
) -> Tool:
    tool = Tool(
        id=uuid.uuid4(),
        identifier=identifier,
        display_name=identifier.split("/")[-1],
        category=category,
        pricing={
            "model": "per_call",
            "base_usd_per_call": base,
            "typical_latency_ms": latency_ms,
        },
        report_count=20,
    )
    db.add(tool)
    await db.flush()
    return tool


class TestCategoryMedianLatency:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_peers(self, db):
        await db.commit()
        assert await _category_median_latency_ms(db, "empty-cat") is None

    @pytest.mark.asyncio
    async def test_median_of_three(self, db):
        await _priced_tool_with_latency(db, "fast", "speedy", 0.001, 200)
        await _priced_tool_with_latency(db, "mid", "speedy", 0.001, 1000)
        await _priced_tool_with_latency(db, "slow", "speedy", 0.001, 3000)
        await db.commit()
        assert await _category_median_latency_ms(db, "speedy") == 1000.0

    @pytest.mark.asyncio
    async def test_thin_category_falls_back_to_global(self, db):
        # "solo" has 1 peer, global pool has 4 → global median wins
        await _priced_tool_with_latency(db, "solo1", "solo", 0.001, 99999)
        await _priced_tool_with_latency(db, "g1", "global", 0.001, 100)
        await _priced_tool_with_latency(db, "g2", "global", 0.001, 500)
        await _priced_tool_with_latency(db, "g3", "global", 0.001, 1500)
        await db.commit()
        # Global pool sorted = [100, 500, 1500, 99999] → median = (500+1500)/2 = 1000
        assert await _category_median_latency_ms(db, "solo") == 1000.0


class TestFinalizeResponseSpeedFirst:
    @pytest.mark.asyncio
    async def test_speed_first_scores_fast_tool_higher_than_slow(self, db):
        # Build three priced peers in the same category, two with latency.
        await _priced_tool_with_latency(db, "peer1", "llm", 0.001, 500)
        await _priced_tool_with_latency(db, "peer2", "llm", 0.003, 1500)
        fast_tool = await _priced_tool_with_latency(db, "fast", "llm", 0.002, 300)
        slow_tool = await _priced_tool_with_latency(db, "slow", "llm", 0.002, 2500)
        await db.commit()

        def _response(reliability: float) -> AssessResponse:
            return AssessResponse(
                reliability_score=reliability,
                confidence=0.85,
                data_source="empirical",
                historical_success_rate="92%",
                predicted_failure_risk="low",
                trend=None,
                common_pitfalls=[],
                recommended_mitigations=[],
                top_alternatives=[],
                estimated_latency_ms=None,
                latency=None,
                last_updated=__import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ),
            )

        fast_resp = _response(90.0)
        slow_resp = _response(90.0)
        await finalize_response(
            fast_resp, db, fast_tool,
            max_price_per_call=None, max_monthly_budget=None,
            expected_calls_per_month=None, expected_tokens=None,
            task_complexity="medium", budget_strategy="speed_first",
        )
        await finalize_response(
            slow_resp, db, slow_tool,
            max_price_per_call=None, max_monthly_budget=None,
            expected_calls_per_month=None, expected_tokens=None,
            task_complexity="medium", budget_strategy="speed_first",
        )

        assert fast_resp.cost_adjusted_score > slow_resp.cost_adjusted_score
        # Reasoning always populated
        assert fast_resp.reasoning is not None and "speed-first" in fast_resp.reasoning
        assert "~300ms" in fast_resp.reasoning
        assert slow_resp.reasoning is not None and "~2500ms" in slow_resp.reasoning

    @pytest.mark.asyncio
    async def test_llm_catalog_recommended_model_populated(self, db):
        # Minimal LLM provider with a model catalog, no DB peers.
        pricing = {
            "model": "per_token",
            "typical_usd_per_call": 0.01,
            "usd_per_million_input_tokens": 3.0,
            "usd_per_million_output_tokens": 15.0,
            "typical_latency_ms": 1200,
            "recommended_model": "sonnet-default",
            "models": [
                {
                    "name": "haiku",
                    "tier": "low",
                    "usd_per_million_input_tokens": 0.8,
                    "usd_per_million_output_tokens": 4.0,
                    "typical_latency_ms": 500,
                },
                {
                    "name": "sonnet",
                    "tier": "medium",
                    "usd_per_million_input_tokens": 3.0,
                    "usd_per_million_output_tokens": 15.0,
                    "typical_latency_ms": 1200,
                },
                {
                    "name": "opus",
                    "tier": "very_high",
                    "usd_per_million_input_tokens": 15.0,
                    "usd_per_million_output_tokens": 75.0,
                    "typical_latency_ms": 2500,
                },
            ],
        }
        tool = Tool(
            id=uuid.uuid4(),
            identifier="https://test.example.com/llm",
            display_name="TestLLM",
            category="LLM APIs",
            pricing=pricing,
            report_count=20,
        )
        db.add(tool)
        await db.commit()

        def _resp():
            return AssessResponse(
                reliability_score=95.0,
                confidence=0.9,
                data_source="empirical",
                historical_success_rate="95%",
                predicted_failure_risk="low",
                trend=None,
                common_pitfalls=[],
                recommended_mitigations=[],
                top_alternatives=[],
                estimated_latency_ms=None,
                latency=None,
                last_updated=__import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ),
            )

        # cost_first + low complexity → haiku
        r = _resp()
        await finalize_response(
            r, db, tool,
            max_price_per_call=None, max_monthly_budget=None,
            expected_calls_per_month=None, expected_tokens=1000,
            task_complexity="low", budget_strategy="cost_first",
        )
        assert r.recommended_model == "haiku"
        # Per-token math: 300 in * 0.8/M + 700 out * 4/M = 0.00024 + 0.00280 = 0.00304
        assert r.price_per_call == pytest.approx(0.00304, rel=1e-3)

        # very_high complexity filters out haiku/sonnet → only opus
        r2 = _resp()
        await finalize_response(
            r2, db, tool,
            max_price_per_call=None, max_monthly_budget=None,
            expected_calls_per_month=None, expected_tokens=1000,
            task_complexity="very_high", budget_strategy="balanced",
        )
        assert r2.recommended_model == "opus"

    @pytest.mark.asyncio
    async def test_task_complexity_default_is_medium(self, db):
        # finalize_response signature default is task_complexity="medium"
        pricing = {
            "model": "per_token",
            "typical_usd_per_call": 0.005,
            "recommended_model": "default-hint",
        }
        tool = Tool(
            id=uuid.uuid4(),
            identifier="https://test.example.com/simple",
            display_name="Simple",
            category="test",
            pricing=pricing,
            report_count=20,
        )
        db.add(tool)
        await db.commit()

        response = AssessResponse(
            reliability_score=90.0,
            confidence=0.8,
            data_source="empirical",
            historical_success_rate="90%",
            predicted_failure_risk="low",
            trend=None,
            common_pitfalls=[],
            recommended_mitigations=[],
            top_alternatives=[],
            estimated_latency_ms=None,
            latency=None,
            last_updated=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
        )
        # NOT passing task_complexity — must default to "medium"
        await finalize_response(
            response, db, tool,
            max_price_per_call=None, max_monthly_budget=None,
            expected_calls_per_month=None, expected_tokens=None,
            budget_strategy="balanced",
        )
        assert response.reasoning is not None
        assert "medium" in response.reasoning
        # String-hint fallback wins since no catalog
        assert response.recommended_model == "default-hint"
