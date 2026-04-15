"""Tests for app.services.discovery — hidden gems + fallback chain ranking.

Regression tests for bug #2 (synthetic reports leaking into discovery) and
bug #3 (Bayesian smoothing missing, so 3/3 outranks 95/100). The fix lives
in `get_hidden_gems` and `get_fallback_chains`:

  - both queries now `NOT IN (_LLM_SYNTHETIC_FINGERPRINTS)` so seed.py and
    llm_*.py bootstrap reports are excluded from the rankings
  - both queries now `ORDER BY smoothed_success_rate` where the smoothed
    rate applies a Bayesian prior (α=5, β=1) matching `scoring.py`
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.security import make_fingerprint
from app.models import Base
from app.models.report import ExecutionReport
from app.models.tool import Tool
from app.services.discovery import get_fallback_chains, get_hidden_gems
from app.services.scoring import _LLM_SYNTHETIC_FINGERPRINTS


TEST_DATABASE_URL = "sqlite+aiosqlite:///test_discovery.db"


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


# ── Helpers ────────────────────────────────────────────────────────────────


async def _create_tool(db, identifier: str, display_name: str | None = None) -> Tool:
    tool = Tool(
        id=uuid.uuid4(),
        identifier=identifier,
        display_name=display_name or identifier,
        category="LLM APIs",
        report_count=0,
    )
    db.add(tool)
    await db.flush()
    return tool


async def _add_fallback_reports(
    db,
    tool: Tool,
    successes: int,
    failures: int,
    *,
    fingerprint: str = "real_agent",
    previous_tool: str = "https://api.primary.example/v1/x",
    attempt_number: int = 2,
):
    """Seed N fallback reports for `tool` (attempt_number >= 2 by default
    so they qualify for the hidden-gems query).

    `previous_tool` matters for the fallback-chain query; default is a
    shared string so several tools can be ranked as fallbacks for the
    same primary.
    """
    now = datetime.now(timezone.utc)
    for i in range(successes):
        db.add(
            ExecutionReport(
                tool_id=tool.id,
                success=True,
                latency_ms=200,
                context_hash="__global__",
                reporter_fingerprint=fingerprint,
                attempt_number=attempt_number,
                previous_tool=previous_tool,
                created_at=now - timedelta(hours=i),
            )
        )
    for i in range(failures):
        db.add(
            ExecutionReport(
                tool_id=tool.id,
                success=False,
                error_category="timeout",
                latency_ms=5000,
                context_hash="__global__",
                reporter_fingerprint=fingerprint,
                attempt_number=attempt_number,
                previous_tool=previous_tool,
                created_at=now - timedelta(hours=successes + i),
            )
        )
    tool.report_count += successes + failures
    await db.flush()


def _synthetic_fingerprint() -> str:
    """Pick one of the three synthetic fingerprints. All three behave the
    same for the filter (they're all in the frozenset)."""
    return make_fingerprint("seed", "seed")


# ── Hidden gems ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hidden_gems_excludes_synthetic_bootstrap_reports(db):
    """A tool whose entire fallback history comes from LLM seed reports
    must NOT appear as a hidden gem. Only real agent journeys count."""
    # Tool A: 10 fallback successes, all from the seed pipeline
    fake_gem = await _create_tool(db, "https://api.fake.example/v1/x", "Fake LLM Gem")
    await _add_fallback_reports(
        db, fake_gem, successes=10, failures=0,
        fingerprint=_synthetic_fingerprint(),
    )

    # Tool B: only 3 real fallback successes — fewer but REAL
    real_gem = await _create_tool(db, "https://api.real.example/v1/x", "Real Gem")
    await _add_fallback_reports(db, real_gem, successes=3, failures=0)

    await db.commit()

    gems = await get_hidden_gems(db)

    tools_returned = [g["tool"] for g in gems]
    assert "https://api.fake.example/v1/x" not in tools_returned, (
        "Synthetic seed reports leaked into hidden-gems ranking"
    )
    assert "https://api.real.example/v1/x" in tools_returned


@pytest.mark.asyncio
async def test_hidden_gems_bayesian_ranking_prefers_large_sample(db):
    """With Bayesian smoothing, 95/100 must outrank 3/3.

    Without the fix this test fails: pure AVG puts `lucky` (100%) above
    `proven` (95%). The smoothed posterior pulls `lucky` down to ~89%
    and leaves `proven` at ~94%, which is the correct ordering.
    """
    lucky = await _create_tool(db, "https://api.lucky.example/v1/x", "Lucky Tool")
    await _add_fallback_reports(db, lucky, successes=3, failures=0)

    proven = await _create_tool(db, "https://api.proven.example/v1/x", "Proven Tool")
    await _add_fallback_reports(db, proven, successes=95, failures=5)

    await db.commit()

    gems = await get_hidden_gems(db)
    tools_in_order = [g["tool"] for g in gems]

    lucky_idx = tools_in_order.index("https://api.lucky.example/v1/x")
    proven_idx = tools_in_order.index("https://api.proven.example/v1/x")
    assert proven_idx < lucky_idx, (
        f"Proven tool (95/100) should rank above Lucky tool (3/3) after "
        f"Bayesian smoothing, but order was {tools_in_order}"
    )


@pytest.mark.asyncio
async def test_hidden_gems_displays_raw_success_rate_not_smoothed(db):
    """Smoothing is applied to the RANKING only — the displayed
    `fallback_success_rate` field must still be the raw percentage so
    existing SDK consumers don't see a silent number change."""
    tool = await _create_tool(db, "https://api.raw.example/v1/x")
    await _add_fallback_reports(db, tool, successes=3, failures=0)
    await db.commit()

    gems = await get_hidden_gems(db)
    match = next(g for g in gems if g["tool"] == "https://api.raw.example/v1/x")
    # 3 successes out of 3 = 100.0% (not the smoothed ~88.9%)
    assert match["fallback_success_rate"] == 100.0
    assert match["times_used_as_fallback"] == 3


# ── Fallback chains ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fallback_chains_excludes_synthetic_reports(db):
    """Same filter on the other discovery query — synthetic reports must
    not pollute the fallback chain for a specific primary tool."""
    primary_url = "https://api.primary.example/v1/x"

    # Fake fallback: 5 synthetic successes pointing at `primary_url`
    fake = await _create_tool(db, "https://api.fake-fallback.example/v1/x")
    await _add_fallback_reports(
        db, fake, successes=5, failures=0,
        fingerprint=_synthetic_fingerprint(),
        previous_tool=primary_url,
    )

    # Real fallback: 2 real successes pointing at the same primary
    real = await _create_tool(db, "https://api.real-fallback.example/v1/x")
    await _add_fallback_reports(
        db, real, successes=2, failures=0,
        previous_tool=primary_url,
    )

    await db.commit()

    chains = await get_fallback_chains(db, tool_identifier=primary_url)
    tools_returned = [c["fallback_tool"] for c in chains]

    assert "https://api.fake-fallback.example/v1/x" not in tools_returned
    assert "https://api.real-fallback.example/v1/x" in tools_returned


@pytest.mark.asyncio
async def test_fallback_chains_bayesian_ranking_prefers_large_sample(db):
    """Smoothed ordering on the fallback-chain query too."""
    primary_url = "https://api.primary2.example/v1/x"

    lucky = await _create_tool(db, "https://api.lucky-fb.example/v1/x")
    await _add_fallback_reports(db, lucky, successes=2, failures=0, previous_tool=primary_url)

    proven = await _create_tool(db, "https://api.proven-fb.example/v1/x")
    await _add_fallback_reports(db, proven, successes=50, failures=3, previous_tool=primary_url)

    await db.commit()

    chains = await get_fallback_chains(db, tool_identifier=primary_url)
    order = [c["fallback_tool"] for c in chains]

    lucky_idx = order.index("https://api.lucky-fb.example/v1/x")
    proven_idx = order.index("https://api.proven-fb.example/v1/x")
    assert proven_idx < lucky_idx, (
        f"50/53 should outrank 2/2 after smoothing; got order {order}"
    )


# ── Sanity: the filter constant we're importing still matches the real one ─


def test_synthetic_fingerprint_constant_still_matches_seed():
    """Guard against the synthetic fingerprint set drifting silently.

    If a new bootstrap source is added in scoring.py's
    _LLM_SYNTHETIC_FINGERPRINTS, this test will NOT catch it — but it
    WILL catch the case where someone removes the `seed` fingerprint
    without realising discovery depends on it.
    """
    assert make_fingerprint("seed", "seed") in _LLM_SYNTHETIC_FINGERPRINTS
    assert make_fingerprint("llm_ondemand", "llm_ondemand") in _LLM_SYNTHETIC_FINGERPRINTS
    assert make_fingerprint("llm_consensus", "llm_consensus") in _LLM_SYNTHETIC_FINGERPRINTS
