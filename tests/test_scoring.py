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
        assert "timeout" in result.common_pitfalls[0]
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

        pitfall_text = " ".join(result.common_pitfalls)
        assert "timeout" in pitfall_text
        assert "rate_limit" in pitfall_text
        assert "auth_failure" in pitfall_text
