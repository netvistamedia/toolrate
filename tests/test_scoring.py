"""Tests for the scoring engine — the core business logic."""

import math
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base
from app.models.tool import Tool
from app.models.report import ExecutionReport
from app.services.scoring import compute_score
from app.config import settings


TEST_DATABASE_URL = "sqlite+aiosqlite:///test_scoring.db"


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


async def _create_tool(db, identifier="test-tool"):
    tool = Tool(id=uuid.uuid4(), identifier=identifier, report_count=0)
    db.add(tool)
    await db.flush()
    return tool


async def _add_reports(db, tool, successes, failures, age_days=0, error_cat="timeout"):
    now = datetime.now(timezone.utc)
    for i in range(successes):
        db.add(ExecutionReport(
            tool_id=tool.id, success=True, latency_ms=200,
            context_hash="__global__", reporter_fingerprint="fp",
            created_at=now - timedelta(days=age_days, hours=i),
        ))
    for i in range(failures):
        db.add(ExecutionReport(
            tool_id=tool.id, success=False, error_category=error_cat,
            latency_ms=5000, context_hash="__global__", reporter_fingerprint="fp",
            created_at=now - timedelta(days=age_days, hours=i),
        ))
    tool.report_count += successes + failures
    await db.flush()


class TestColdStart:
    """Tools with no data should return Bayesian prior."""

    @pytest.mark.asyncio
    async def test_cold_start_score(self, db):
        tool = await _create_tool(db)
        await db.commit()
        result = await compute_score(db, tool, "__global__")

        expected = settings.bayesian_alpha_prior / (settings.bayesian_alpha_prior + settings.bayesian_beta_prior)
        assert result.reliability_score == round(expected * 100, 1)
        assert result.confidence == 0.0
        assert result.predicted_failure_risk == "unknown"
        assert result.common_pitfalls == []

    @pytest.mark.asyncio
    async def test_cold_start_no_alternatives(self, db):
        tool = await _create_tool(db)
        await db.commit()
        result = await compute_score(db, tool, "__global__")
        assert result.top_alternatives == []


class TestAllSuccess:
    """Tools with 100% success rate."""

    @pytest.mark.asyncio
    async def test_high_score(self, db):
        tool = await _create_tool(db)
        await _add_reports(db, tool, successes=50, failures=0)
        await db.commit()
        result = await compute_score(db, tool, "__global__")

        # Should be close to 100 but not exactly due to Bayesian prior
        assert result.reliability_score > 95
        assert result.predicted_failure_risk == "low"

    @pytest.mark.asyncio
    async def test_no_pitfalls(self, db):
        tool = await _create_tool(db)
        await _add_reports(db, tool, successes=20, failures=0)
        await db.commit()
        result = await compute_score(db, tool, "__global__")
        assert result.common_pitfalls == []
        assert result.recommended_mitigations == []


class TestAllFailure:
    """Tools with 100% failure rate."""

    @pytest.mark.asyncio
    async def test_low_score(self, db):
        tool = await _create_tool(db)
        await _add_reports(db, tool, successes=0, failures=50, error_cat="timeout")
        await db.commit()
        result = await compute_score(db, tool, "__global__")

        assert result.reliability_score < 20
        assert result.predicted_failure_risk == "high"

    @pytest.mark.asyncio
    async def test_pitfalls_listed(self, db):
        tool = await _create_tool(db)
        await _add_reports(db, tool, successes=0, failures=30, error_cat="timeout")
        await db.commit()
        result = await compute_score(db, tool, "__global__")

        assert len(result.common_pitfalls) > 0
        assert result.common_pitfalls[0].category == "timeout"
        assert result.common_pitfalls[0].count > 0
        assert len(result.recommended_mitigations) > 0


class TestMixedResults:
    """Tools with mixed success/failure."""

    @pytest.mark.asyncio
    async def test_80_percent_success(self, db):
        tool = await _create_tool(db)
        await _add_reports(db, tool, successes=80, failures=20, error_cat="rate_limit")
        await db.commit()
        result = await compute_score(db, tool, "__global__")

        # Score should be around 80, adjusted by Bayesian prior
        assert 70 < result.reliability_score < 90

    @pytest.mark.asyncio
    async def test_confidence_increases_with_data(self, db):
        tool1 = await _create_tool(db, "tool-few")
        await _add_reports(db, tool1, successes=5, failures=0)

        tool2 = await _create_tool(db, "tool-many")
        await _add_reports(db, tool2, successes=100, failures=0)
        await db.commit()

        result_few = await compute_score(db, tool1, "__global__")
        result_many = await compute_score(db, tool2, "__global__")

        assert result_many.confidence > result_few.confidence


class TestRecencyWeighting:
    """Recent reports should matter more than old ones."""

    @pytest.mark.asyncio
    async def test_recent_failures_lower_score(self, db):
        tool = await _create_tool(db)
        # Old reports: all success (20+ days ago)
        await _add_reports(db, tool, successes=30, failures=0, age_days=25)
        # Recent reports: all failure (today)
        await _add_reports(db, tool, successes=0, failures=10, age_days=0, error_cat="timeout")
        await db.commit()
        result = await compute_score(db, tool, "__global__")

        # Despite 30 successes vs 10 failures overall, recent failures should drag score down
        assert result.reliability_score < 50

    @pytest.mark.asyncio
    async def test_recent_success_higher_score(self, db):
        tool = await _create_tool(db)
        # Old reports: all failure (20+ days ago)
        await _add_reports(db, tool, successes=0, failures=30, age_days=25, error_cat="timeout")
        # Recent reports: all success (today)
        await _add_reports(db, tool, successes=10, failures=0, age_days=0)
        await db.commit()
        result = await compute_score(db, tool, "__global__")

        # Recent successes should boost score despite old failures
        assert result.reliability_score > 70


class TestLatency:
    """Latency should be correctly computed."""

    @pytest.mark.asyncio
    async def test_average_latency(self, db):
        tool = await _create_tool(db)
        now = datetime.now(timezone.utc)
        for latency in [100, 200, 300]:
            db.add(ExecutionReport(
                tool_id=tool.id, success=True, latency_ms=latency,
                context_hash="__global__", reporter_fingerprint="fp",
                created_at=now,
            ))
        tool.report_count = 3
        await db.commit()
        result = await compute_score(db, tool, "__global__")

        assert result.estimated_latency_ms == 200  # avg of 100, 200, 300


class TestMultipleErrorCategories:
    """Multiple error types should all appear in pitfalls."""

    @pytest.mark.asyncio
    async def test_multiple_pitfalls(self, db):
        tool = await _create_tool(db)
        await _add_reports(db, tool, successes=50, failures=0)
        await _add_reports(db, tool, successes=0, failures=10, error_cat="timeout")
        await _add_reports(db, tool, successes=0, failures=5, error_cat="rate_limit")
        await _add_reports(db, tool, successes=0, failures=3, error_cat="auth_failure")
        await db.commit()
        result = await compute_score(db, tool, "__global__")

        pitfall_categories = [p.category for p in result.common_pitfalls]
        assert "timeout" in pitfall_categories
        assert "rate_limit" in pitfall_categories
        assert "auth_failure" in pitfall_categories


class TestRecencyWeightedPitfalls:
    """Pitfall ranking and percentages must use the recency weight, not raw counts."""

    @pytest.mark.asyncio
    async def test_recent_category_outranks_old_volume(self, db):
        """100 ancient timeouts should not outrank 10 fresh rate_limits.

        Without recency weighting on error_counts, the surfaced top pitfall
        was always the highest-volume historical category, drowning out the
        live problem the agent should react to.
        """
        tool = await _create_tool(db)
        # Old, large-volume category (25 days ago — well past the 3.5d half-life)
        await _add_reports(db, tool, successes=0, failures=100, age_days=25, error_cat="timeout")
        # Recent, lower-volume category (today)
        await _add_reports(db, tool, successes=0, failures=10, age_days=0, error_cat="rate_limit")
        await db.commit()

        result = await compute_score(db, tool, "__global__")
        assert result.common_pitfalls, "expected at least one pitfall surfaced"
        assert result.common_pitfalls[0].category == "rate_limit", (
            "fresh rate_limit should outrank a much older timeout pile once "
            "error counts are recency-weighted"
        )

    @pytest.mark.asyncio
    async def test_pitfall_percentages_use_weighted_denominator(self, db):
        """Percentages should sum to ~100 across the surfaced categories.

        With raw-count percentages and weighted ordering, a tool that had
        most failures aging out could surface a top pitfall at "3%" — clearly
        wrong. The fix uses the same weight on numerator and denominator.
        """
        tool = await _create_tool(db)
        await _add_reports(db, tool, successes=0, failures=20, age_days=0, error_cat="timeout")
        await _add_reports(db, tool, successes=0, failures=10, age_days=0, error_cat="rate_limit")
        await db.commit()

        result = await compute_score(db, tool, "__global__")
        total_pct = sum(p.percentage for p in result.common_pitfalls)
        # Two categories, both with same age → ratios should be ~67/33.
        assert 95 <= total_pct <= 105, (
            f"weighted-pct categories should sum to ~100, got {total_pct} "
            f"({[(p.category, p.percentage) for p in result.common_pitfalls]})"
        )


class TestHistoricalSuccessRate:
    """historical_success_rate should mirror reliability_score's recency
    weighting, so a tool can't show "30% historical / 78% reliability" — two
    numbers from the same data that diverge by 40+ pp because one ignored age.
    """

    @pytest.mark.asyncio
    async def test_old_failures_fade_from_displayed_rate(self, db):
        tool = await _create_tool(db)
        # Inside the 30-day lookback but well past the 3.5-day half-life:
        # ~exp(-20 * ln(2)/3.5) ≈ 0.02 weight per failure.
        await _add_reports(db, tool, successes=0, failures=100, age_days=20)
        # Today: weight ≈ 1.0 per success.
        await _add_reports(db, tool, successes=10, failures=0, age_days=0)
        await db.commit()

        result = await compute_score(db, tool, "__global__")
        # Raw rate would be 10/110 = 9%. Weighted rate is ~10/(10 + 100*0.02)
        # = 10/12 ≈ 83% — close to the reliability_score and far from 9%.
        displayed = int(result.historical_success_rate.split("%")[0])
        assert displayed >= 70, (
            f"historical_success_rate should reflect recency weighting; got "
            f"{result.historical_success_rate} for 100 aging failures + "
            f"10 fresh successes"
        )
        # Total call count is still raw — "we have 110 data points" is honest
        # even when most of them are barely contributing to the rate.
        assert "110 calls" in result.historical_success_rate


class TestEffectiveSampleSize:
    """Confidence should use Kish's effective sample size, not raw Σw."""

    @pytest.mark.asyncio
    async def test_uniform_recent_weights_collapse_to_n(self, db):
        """When every weight ≈ 1 (all reports are very recent), Kish's
        formula collapses to ``n`` — same answer as the previous code."""
        tool = await _create_tool(db)
        await _add_reports(db, tool, successes=50, failures=0, age_days=0)
        await db.commit()
        result = await compute_score(db, tool, "__global__")
        assert result.confidence > 0.6  # ~50 effective samples

    @pytest.mark.asyncio
    async def test_one_recent_with_old_history_lowers_confidence(self, db):
        """50 ancient reports + 1 fresh one used to give nearly the same
        confidence as 51 fresh — the old (Σw) formula treated the recent
        report as worth ~50× more confidence than it really is. Kish's
        formula correctly down-weights to roughly the effective sample
        the data supports."""
        tool_uniform = await _create_tool(db, "uniform")
        await _add_reports(db, tool_uniform, successes=51, failures=0, age_days=0)

        tool_skewed = await _create_tool(db, "skewed")
        await _add_reports(db, tool_skewed, successes=50, failures=0, age_days=20)
        await _add_reports(db, tool_skewed, successes=1, failures=0, age_days=0)

        await db.commit()
        uniform = await compute_score(db, tool_uniform, "__global__")
        skewed = await compute_score(db, tool_skewed, "__global__")

        # Skewed sample should report STRICTLY lower confidence than the
        # equivalent-volume uniform sample under the corrected formula.
        assert skewed.confidence < uniform.confidence


class TestSdkSkipMarkersExcluded:
    """SDK telemetry rows must not affect reliability scoring."""

    @pytest.mark.asyncio
    async def test_skipped_low_score_does_not_lower_reliability(self, db):
        """Skipped tools are caller-choice, not tool failures."""
        tool_clean = await _create_tool(db, "clean")
        await _add_reports(db, tool_clean, successes=50, failures=0)

        tool_skipped = await _create_tool(db, "skipped")
        await _add_reports(db, tool_skipped, successes=50, failures=0)
        # Pretend the SDK marked 30 calls as skipped — currently they would
        # nuke the reliability score; after the fix, they are filtered out.
        await _add_reports(
            db, tool_skipped, successes=0, failures=30,
            error_cat="skipped_low_score",
        )
        await db.commit()

        clean_result = await compute_score(db, tool_clean, "__global__")
        skipped_result = await compute_score(db, tool_skipped, "__global__")
        assert skipped_result.reliability_score == clean_result.reliability_score

    @pytest.mark.asyncio
    async def test_skipped_over_budget_not_in_pitfalls(self, db):
        tool = await _create_tool(db)
        await _add_reports(db, tool, successes=10, failures=0)
        await _add_reports(
            db, tool, successes=0, failures=10,
            error_cat="skipped_over_budget",
        )
        await db.commit()
        result = await compute_score(db, tool, "__global__")
        categories = [p.category for p in result.common_pitfalls]
        assert "skipped_over_budget" not in categories
        assert "skipped_low_score" not in categories
