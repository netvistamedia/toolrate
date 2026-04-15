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
    _annotate_alternatives_within_budget,
    _apply_cost_adjustment,
    _budget_explanation,
    _category_median_cost,
    _cost_adjusted_score,
    _effective_cost,
    _is_within_budget,
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


class TestCostAdjustedScore:
    def test_strategy_weights_sum_to_one(self):
        for strategy, (w_rel, w_cost) in _STRATEGY_WEIGHTS.items():
            assert w_rel + w_cost == pytest.approx(1.0), strategy

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

    def test_tool_without_pricing_and_no_budget_leaves_everything_none(self):
        resp = self._make_response()
        tool = self._make_tool(None)
        _apply_cost_adjustment(
            resp, tool,
            max_price_per_call=None, max_monthly_budget=None,
            expected_calls_per_month=None, budget_strategy="reliability_first",
            category_median=0.01,
        )
        assert resp.price_per_call is None
        assert resp.pricing_model is None
        assert resp.cost_adjusted_score is None
        assert resp.within_budget is None
        assert resp.budget_explanation is None

    def test_tool_without_pricing_with_budget_explains(self):
        resp = self._make_response()
        tool = self._make_tool(None)
        _apply_cost_adjustment(
            resp, tool,
            max_price_per_call=0.01, max_monthly_budget=None,
            expected_calls_per_month=None, budget_strategy="reliability_first",
            category_median=0.01,
        )
        assert resp.budget_explanation == "No pricing data available for this tool."

    def test_tool_with_pricing_populates_cost_fields(self):
        resp = self._make_response(reliability=90.0)
        tool = self._make_tool({
            "model": "per_call",
            "base_usd_per_call": 0.005,
            "typical_usd_per_call": None,
        })
        _apply_cost_adjustment(
            resp, tool,
            max_price_per_call=None, max_monthly_budget=None,
            expected_calls_per_month=None, budget_strategy="reliability_first",
            category_median=0.01,
        )
        assert resp.price_per_call == 0.005
        assert resp.pricing_model == "per_call"
        # cost_norm = 0.005/0.01 = 0.5 → cost side = 50
        # reliability_first: 0.80 * 90 + 0.20 * 50 = 72 + 10 = 82
        assert resp.cost_adjusted_score == 82.0

    def test_expected_calls_drives_estimated_monthly_cost(self):
        resp = self._make_response()
        tool = self._make_tool({"model": "per_call", "base_usd_per_call": 0.001})
        _apply_cost_adjustment(
            resp, tool,
            max_price_per_call=None, max_monthly_budget=None,
            expected_calls_per_month=10000,
            budget_strategy="reliability_first",
            category_median=0.001,
        )
        assert resp.estimated_monthly_cost == 10.0  # 10000 * 0.001
        assert resp.budget_explanation is not None
        assert "10.00" in resp.budget_explanation

    def test_over_budget_sets_within_budget_false_and_flag(self):
        resp = self._make_response()
        tool = self._make_tool({"model": "per_call", "base_usd_per_call": 0.10})
        _apply_cost_adjustment(
            resp, tool,
            max_price_per_call=0.01, max_monthly_budget=None,
            expected_calls_per_month=None, budget_strategy="balanced",
            category_median=0.01,
        )
        assert resp.within_budget is False
        assert "exceeds" in resp.budget_explanation

    def test_different_strategies_produce_different_scores(self):
        tool = self._make_tool({"model": "per_call", "base_usd_per_call": 0.02})
        scores: dict[str, float] = {}
        for strategy in ("reliability_first", "balanced", "cost_first"):
            resp = self._make_response(reliability=90.0)
            _apply_cost_adjustment(
                resp, tool,
                max_price_per_call=None, max_monthly_budget=None,
                expected_calls_per_month=None, budget_strategy=strategy,
                category_median=0.01,
            )
            scores[strategy] = resp.cost_adjusted_score

        # Expensive tool (2x median) should score worst under cost_first
        # and best under reliability_first.
        assert scores["reliability_first"] > scores["balanced"]
        assert scores["balanced"] > scores["cost_first"]


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
    # The median cache is process-global — each test expects a fresh state.
    _CATEGORY_MEDIAN_CACHE.clear()


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
