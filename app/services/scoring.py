import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.report import ExecutionReport
from app.models.tool import Tool
from app.models.alternative import Alternative
from app.models.score_cache import ScoreSnapshot
from app.schemas.assess import AssessResponse, AlternativeTool

# Pre-defined mitigations for known error categories
MITIGATIONS = {
    "timeout": "Increase timeout to 30s; implement retry with exponential backoff",
    "rate_limit": "Add request throttling; use credential rotation if available",
    "auth_failure": "Verify credentials before batch operations; check token expiry",
    "connection_error": "Implement circuit breaker pattern; add fallback endpoint",
    "validation_error": "Validate payload schema before sending; check API version",
    "server_error": "Implement retry with backoff; consider alternative provider",
    "not_found": "Verify resource exists before operating; check API endpoint URL",
    "permission_denied": "Check API key scopes; verify account permissions",
}


async def compute_score(
    db: AsyncSession,
    tool: Tool,
    context_hash: str,
    data_pool: str | None = None,
) -> AssessResponse:
    now = datetime.now(timezone.utc)
    cutoff_30d = now - timedelta(days=30)
    cutoff_7d = now - timedelta(days=7)
    cutoff_24h = now - timedelta(hours=24)
    halflife = settings.score_decay_halflife_days
    decay_lambda = math.log(2) / halflife

    # Fetch reports for the last 30 days
    query = (
        select(ExecutionReport)
        .where(
            ExecutionReport.tool_id == tool.id,
            ExecutionReport.created_at >= cutoff_30d,
        )
        .order_by(ExecutionReport.created_at.desc())
        .limit(settings.max_reports_per_query)
    )

    # Try context-specific first
    if context_hash != "__global__":
        ctx_query = query.where(ExecutionReport.context_hash == context_hash)
        if data_pool:
            ctx_query = ctx_query.where(ExecutionReport.data_pool == data_pool)
        result = await db.execute(ctx_query)
        reports = list(result.scalars().all())

        # Fall back to global if not enough context-specific data
        if len(reports) < 5:
            global_query = query
            if data_pool:
                global_query = global_query.where(ExecutionReport.data_pool == data_pool)
            result = await db.execute(global_query)
            reports = list(result.scalars().all())
    else:
        if data_pool:
            query = query.where(ExecutionReport.data_pool == data_pool)
        result = await db.execute(query)
        reports = list(result.scalars().all())

    # Cold start — no reports at all
    if not reports:
        return _cold_start_response(now)

    # Step 1: Recency-weighted success rate
    weighted_successes = 0.0
    weighted_failures = 0.0
    total_weight = 0.0
    latencies = []
    error_counts: dict[str, int] = {}
    reports_7d = 0
    successes_7d = 0
    successes_24h = 0
    reports_24h = 0

    for report in reports:
        age_days = (now - report.created_at).total_seconds() / 86400
        weight = math.exp(-decay_lambda * age_days)

        if report.success:
            weighted_successes += weight
        else:
            weighted_failures += weight
            if report.error_category:
                error_counts[report.error_category] = error_counts.get(report.error_category, 0) + 1

        total_weight += weight

        if report.latency_ms is not None:
            latencies.append(report.latency_ms)

        if report.created_at >= cutoff_7d:
            reports_7d += 1
            if report.success:
                successes_7d += 1

        if report.created_at >= cutoff_24h:
            reports_24h += 1
            if report.success:
                successes_24h += 1

    # Step 2: Bayesian smoothing
    alpha = settings.bayesian_alpha_prior + weighted_successes
    beta = settings.bayesian_beta_prior + weighted_failures
    reliability = alpha / (alpha + beta)

    # Step 3: Confidence
    n_eff = total_weight
    confidence = 1 - 1 / (1 + math.sqrt(n_eff / 10))

    # Step 4: Failure risk with trend adjustment
    failure_risk = 1 - reliability
    if reports_7d > 0 and reports_24h > 0:
        sr_7d = successes_7d / reports_7d
        sr_24h = successes_24h / reports_24h
        if sr_24h < sr_7d:
            trend_penalty = (sr_7d - sr_24h) * 0.5
            failure_risk = min(1.0, failure_risk + trend_penalty)

    risk_label = "low" if failure_risk < 0.15 else "medium" if failure_risk < 0.35 else "high"

    # Step 5: Success rate strings
    total = len(reports)
    successes_total = sum(1 for r in reports if r.success)
    sr_30d = round(successes_total / total * 100) if total else 0
    success_rate_str = f"{sr_30d}% (last 30 days, {total} calls)"

    # Step 6: Common pitfalls and mitigations
    sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    pitfalls = []
    mitigations = []
    for category, count in sorted_errors:
        pct = round(count / total * 100)
        pitfalls.append(f"{category} ({pct}% of failures)")
        if category in MITIGATIONS:
            mitigations.append(MITIGATIONS[category])

    # Step 7: Latency
    avg_latency = round(sum(latencies) / len(latencies)) if latencies else None

    # Step 8: Alternatives
    alternatives = await _get_alternatives(db, tool.id)

    return AssessResponse(
        reliability_score=round(reliability * 100, 1),
        confidence=round(confidence, 2),
        historical_success_rate=success_rate_str,
        predicted_failure_risk=risk_label,
        common_pitfalls=pitfalls,
        recommended_mitigations=mitigations,
        top_alternatives=alternatives,
        estimated_latency_ms=avg_latency,
        last_updated=now,
    )


def _cold_start_response(now: datetime) -> AssessResponse:
    """Response for tools with no data — uses Bayesian prior."""
    alpha = settings.bayesian_alpha_prior
    beta = settings.bayesian_beta_prior
    reliability = alpha / (alpha + beta)
    return AssessResponse(
        reliability_score=round(reliability * 100, 1),
        confidence=0.0,
        historical_success_rate="No data available",
        predicted_failure_risk="unknown",
        common_pitfalls=[],
        recommended_mitigations=[],
        top_alternatives=[],
        estimated_latency_ms=None,
        last_updated=now,
    )


async def _get_alternatives(db: AsyncSession, tool_id) -> list[AlternativeTool]:
    result = await db.execute(
        select(Alternative, Tool)
        .join(Tool, Alternative.alternative_tool_id == Tool.id)
        .where(Alternative.tool_id == tool_id)
        .order_by(Alternative.relevance_score.desc())
        .limit(3)
    )
    alternatives = []
    for alt, alt_tool in result.tuples().all():
        alternatives.append(
            AlternativeTool(
                tool=alt_tool.identifier,
                score=round(alt.relevance_score * 100, 1),
                reason="Alternative provider",
            )
        )
    return alternatives
