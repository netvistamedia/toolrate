"""Admin-only endpoints — platform-wide insights for the dashboard.

Gated by `require_admin_key`: any non-admin API key is rejected with 403.
All aggregations are bounded by time windows so none of them scan the full
reports table.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from sqlalchemy import and_, case, func, select

from app.core.security import make_fingerprint
from app.dependencies import AdminKey, Db, RedisClient
from app.models.api_key import ApiKey
from app.models.report import ExecutionReport
from app.models.tool import Tool

router = APIRouter()


# Synthetic fingerprints produced by the bootstrap/seed paths. These aren't
# real agent traffic — they're used to prime the scoring model for newly
# discovered tools — so the dashboard excludes them from every real-traffic
# counter and surfaces them separately in a "synthetic activity" tile.
SYNTHETIC_FINGERPRINTS: tuple[str, ...] = (
    make_fingerprint("seed", "seed"),
    make_fingerprint("llm_ondemand", "llm_ondemand"),
    make_fingerprint("llm_consensus", "llm_consensus"),
)


def _only_real():
    """SQLAlchemy predicate that excludes synthetic reports."""
    return ExecutionReport.reporter_fingerprint.notin_(SYNTHETIC_FINGERPRINTS)


def _bucket_rows_by_hour(rows: list[tuple[datetime, bool]]) -> list[dict]:
    """Group (created_at, success) rows into hourly buckets. Cross-DB; bounded
    to 24h windows so memory footprint is small even at high traffic."""
    buckets: dict[datetime, int] = defaultdict(int)
    for created_at, _success in rows:
        hour = created_at.replace(minute=0, second=0, microsecond=0)
        buckets[hour] += 1
    return [
        {"t": h.isoformat(), "count": n}
        for h, n in sorted(buckets.items())
    ]


def _bucket_rows_by_day(rows: list[tuple[datetime, bool]]) -> list[dict]:
    """Group (created_at, success) rows into daily buckets with success rate."""
    totals: dict[datetime, int] = defaultdict(int)
    successes: dict[datetime, int] = defaultdict(int)
    for created_at, success in rows:
        day = created_at.replace(hour=0, minute=0, second=0, microsecond=0)
        totals[day] += 1
        if success:
            successes[day] += 1
    return [
        {
            "t": d.isoformat(),
            "count": totals[d],
            "success_rate": (successes[d] / totals[d]) if totals[d] else None,
        }
        for d in sorted(totals)
    ]


# Histogram buckets for tool reliability scores (success rate).
SCORE_BUCKETS = [
    ("0-20",  0,   0.2),
    ("20-40", 0.2, 0.4),
    ("40-60", 0.4, 0.6),
    ("60-80", 0.6, 0.8),
    ("80-100", 0.8, 1.01),
]


@router.get(
    "/admin/dashboard",
    tags=["Admin"],
    summary="Platform dashboard — today, trends, reliability, top activity",
    description=(
        "Single-shot aggregation for the admin dashboard. "
        "Requires an API key with `tier = admin`. "
        "Covers today's counters, 24h + 30d trends, reliability distribution, "
        "top tools by activity and failure rate, error category breakdown, and "
        "a billing snapshot."
    ),
    # Hidden from the public OpenAPI/Swagger UI — this endpoint only serves
    # the internal admin dashboard and doesn't need to advertise itself to
    # random API explorers.
    include_in_schema=False,
)
async def admin_dashboard(db: Db, redis: RedisClient, api_key: AdminKey):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_24h = now - timedelta(hours=24)
    prev_24h = now - timedelta(hours=48)
    last_30d = now - timedelta(days=30)

    # ── Today's counters (real traffic only) ────────────────────────
    reports_today = (await db.execute(
        select(
            func.count(),
            func.sum(case((ExecutionReport.success == True, 1), else_=0)),  # noqa: E712
            func.sum(case((ExecutionReport.success == False, 1), else_=0)),  # noqa: E712
            func.count(func.distinct(ExecutionReport.reporter_fingerprint)),
            func.count(func.distinct(ExecutionReport.tool_id)),
        ).where(
            ExecutionReport.created_at >= today_start,
            _only_real(),
        )
    )).one()

    total_today, success_today, fail_today, unique_reporters_today, tools_touched_today = reports_today
    total_today = int(total_today or 0)
    success_today = int(success_today or 0)
    fail_today = int(fail_today or 0)
    success_rate_today = (success_today / total_today * 100) if total_today else None

    # Synthetic bootstrap counter (for transparency — shows whether the LLM
    # bootstrap is actively priming new tools today)
    synthetic_today = (await db.execute(
        select(func.count()).select_from(ExecutionReport)
        .where(
            ExecutionReport.created_at >= today_start,
            ExecutionReport.reporter_fingerprint.in_(SYNTHETIC_FINGERPRINTS),
        )
    )).scalar() or 0

    # New signups today (API keys created since midnight UTC)
    signups_today = (await db.execute(
        select(func.count()).select_from(ApiKey)
        .where(ApiKey.created_at >= today_start)
    )).scalar() or 0

    # ── 24h hourly trend + 30d daily trend ──────────────────────────
    # We fetch (created_at, success) rows in two windows and bucket them in
    # Python. Cross-DB (Postgres + SQLite-for-tests) and bounded in size by
    # the time window.
    hourly_rows = (await db.execute(
        select(ExecutionReport.created_at, ExecutionReport.success)
        .where(ExecutionReport.created_at >= last_24h, _only_real())
    )).all()
    hourly_trend = _bucket_rows_by_hour(
        [(r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=timezone.utc),
          r.success) for r in hourly_rows]
    )

    daily_rows_raw = (await db.execute(
        select(ExecutionReport.created_at, ExecutionReport.success)
        .where(ExecutionReport.created_at >= last_30d, _only_real())
    )).all()
    daily_trend = _bucket_rows_by_day(
        [(r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=timezone.utc),
          r.success) for r in daily_rows_raw]
    )

    # ── Reliability histogram across tools with ≥5 REAL reports ─────
    per_tool_rows = (await db.execute(
        select(
            ExecutionReport.tool_id,
            func.count().label("n"),
            func.avg(case((ExecutionReport.success == True, 1.0), else_=0.0)).label("rate"),  # noqa: E712
        )
        .where(ExecutionReport.created_at >= last_30d, _only_real())
        .group_by(ExecutionReport.tool_id)
        .having(func.count() >= 5)
    )).all()

    histogram = {label: 0 for label, _, _ in SCORE_BUCKETS}
    at_risk = healthy = 0
    rates = []
    for _, _n, rate in per_tool_rows:
        rate = float(rate or 0)
        rates.append(rate)
        if rate < 0.6:
            at_risk += 1
        elif rate >= 0.8:
            healthy += 1
        for label, lo, hi in SCORE_BUCKETS:
            if lo <= rate < hi:
                histogram[label] += 1
                break
    avg_reliability = (sum(rates) / len(rates)) if rates else None

    # ── Top 10 busiest tools in last 24h (real traffic) ──────────────
    busiest_rows = (await db.execute(
        select(
            Tool.identifier,
            Tool.display_name,
            func.count().label("reports_24h"),
            func.avg(case((ExecutionReport.success == True, 1.0), else_=0.0)).label("rate"),  # noqa: E712
        )
        .join(ExecutionReport, ExecutionReport.tool_id == Tool.id)
        .where(ExecutionReport.created_at >= last_24h, _only_real())
        .group_by(Tool.id, Tool.identifier, Tool.display_name)
        .order_by(func.count().desc())
        .limit(10)
    )).all()
    busiest = [
        {
            "identifier": r.identifier,
            "display_name": r.display_name,
            "reports_24h": int(r.reports_24h),
            "success_rate": float(r.rate or 0),
        }
        for r in busiest_rows
    ]

    # ── Top 10 most-failing tools in last 24h (real traffic, min 5) ──
    failing_rows = (await db.execute(
        select(
            Tool.identifier,
            Tool.display_name,
            func.count().label("reports_24h"),
            func.avg(case((ExecutionReport.success == True, 1.0), else_=0.0)).label("rate"),  # noqa: E712
        )
        .join(ExecutionReport, ExecutionReport.tool_id == Tool.id)
        .where(ExecutionReport.created_at >= last_24h, _only_real())
        .group_by(Tool.id, Tool.identifier, Tool.display_name)
        .having(func.count() >= 5)
        .order_by(func.avg(case((ExecutionReport.success == True, 1.0), else_=0.0)).asc())  # noqa: E712
        .limit(10)
    )).all()
    failing = [
        {
            "identifier": r.identifier,
            "display_name": r.display_name,
            "reports_24h": int(r.reports_24h),
            "success_rate": float(r.rate or 0),
        }
        for r in failing_rows
    ]

    # ── Error category breakdown today (real traffic) ───────────────
    error_rows = (await db.execute(
        select(ExecutionReport.error_category, func.count())
        .where(and_(
            ExecutionReport.created_at >= today_start,
            ExecutionReport.success == False,  # noqa: E712
            ExecutionReport.error_category.isnot(None),
            _only_real(),
        ))
        .group_by(ExecutionReport.error_category)
        .order_by(func.count().desc())
    )).all()
    errors_today = [
        {"category": category or "unknown", "count": int(count)}
        for category, count in error_rows
    ]

    # ── Platform totals ─────────────────────────────────────────────
    total_tools = (await db.execute(select(func.count()).select_from(Tool))).scalar() or 0
    total_reports = (await db.execute(select(func.count()).select_from(ExecutionReport))).scalar() or 0
    total_keys = (await db.execute(
        select(func.count()).select_from(ApiKey).where(ApiKey.is_active == True)  # noqa: E712
    )).scalar() or 0

    # ── Tier breakdown ──────────────────────────────────────────────
    tier_rows = (await db.execute(
        select(ApiKey.tier, func.count())
        .where(ApiKey.is_active == True)  # noqa: E712
        .group_by(ApiKey.tier)
    )).all()
    tier_breakdown = {row[0]: int(row[1]) for row in tier_rows}

    # ── Registration source breakdown ───────────────────────────────
    # Splits new signups by their `source` provenance tag (web, mcp, cli,
    # …). NULL means the key predates the source column (added 2026-04-20)
    # and is bucketed as "(legacy)" in the UI. Three windows so the
    # dashboard can show "is the launch landing right now?" at a glance.
    last_7d = now - timedelta(days=7)

    async def _source_counts(since: datetime | None) -> dict[str | None, int]:
        stmt = select(ApiKey.source, func.count()).group_by(ApiKey.source)
        if since is not None:
            stmt = stmt.where(ApiKey.created_at >= since)
        return {row[0]: int(row[1]) for row in (await db.execute(stmt)).all()}

    src_24h = await _source_counts(last_24h)
    src_7d = await _source_counts(last_7d)
    src_all = await _source_counts(None)

    # Stable ordering: known channels first (alphabetical), then NULL bucket.
    known = sorted({s for s in (set(src_24h) | set(src_7d) | set(src_all)) if s is not None})
    rows = [
        {
            "source": s,
            "last_24h": int(src_24h.get(s, 0)),
            "last_7d": int(src_7d.get(s, 0)),
            "all_time": int(src_all.get(s, 0)),
        }
        for s in known
    ]
    if None in src_all:
        rows.append({
            "source": None,
            "last_24h": int(src_24h.get(None, 0)),
            "last_7d": int(src_7d.get(None, 0)),
            "all_time": int(src_all.get(None, 0)),
        })

    # ── Billing snapshot — sum PAYG billable counters across keys ───
    # Redis layout from app/services/payg_meter.py:
    #   payg_billable:{key_hash}:{YYYY-MM} → int (monthly billable calls)
    billable_month_total = 0
    try:
        async for key in redis.scan_iter(
            match=f"payg_billable:*:{now.strftime('%Y-%m')}"
        ):
            val = await redis.get(key)
            billable_month_total += int(val or 0)
    except Exception:
        pass

    return {
        "generated_at": now.isoformat(),
        "today": {
            "reports_total": total_today,
            "reports_successful": success_today,
            "reports_failed": fail_today,
            "success_rate_pct": round(success_rate_today, 1) if success_rate_today is not None else None,
            "unique_reporters": int(unique_reporters_today or 0),
            "tools_touched": int(tools_touched_today or 0),
            "new_signups": int(signups_today),
            "synthetic_bootstrap_reports": int(synthetic_today),
        },
        "trend": {
            "hourly_24h": hourly_trend,
            "daily_30d": daily_trend,
        },
        "reliability": {
            "avg_success_rate": round(avg_reliability, 4) if avg_reliability is not None else None,
            "at_risk_tools": at_risk,        # success_rate < 0.6
            "healthy_tools": healthy,        # success_rate ≥ 0.8
            "histogram": histogram,
            "sample_size": len(rates),
        },
        "top_tools": {
            "busiest_24h": busiest,
            "most_failing_24h": failing,
        },
        "errors_today": errors_today,
        "totals": {
            "tools": int(total_tools),
            "reports": int(total_reports),
            "active_keys": int(total_keys),
            "by_tier": tier_breakdown,
        },
        "registration_sources": rows,
        "billing": {
            "payg_billable_month_to_date": billable_month_total,
            "payg_keys": tier_breakdown.get("payg", 0),
            "pro_keys": tier_breakdown.get("pro", 0),
            "enterprise_keys": tier_breakdown.get("enterprise", 0),
        },
    }
