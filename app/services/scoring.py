import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import make_fingerprint
from app.models.report import ExecutionReport
from app.models.tool import Tool
from app.models.alternative import Alternative
from app.schemas.assess import AssessResponse, AlternativeTool, PitfallDetail, TrendInfo, LatencyInfo
from app.services.jurisdiction import (
    classify_jurisdiction,
    data_residency_risk,
    format_hosting_jurisdiction,
    is_gdpr_compliant,
    recommended_for,
)

# Synthetic fingerprints used by the LLM bootstrap paths (seed.py,
# import_assessments.py, llm_assess.py). When all of a tool's recent reports
# carry one of these, we mark data_source as "llm_estimated" so callers know
# the score is from model consensus, not empirical traffic.
_LLM_SYNTHETIC_FINGERPRINTS: frozenset[str] = frozenset({
    make_fingerprint("seed", "seed"),
    make_fingerprint("llm_ondemand", "llm_ondemand"),
    make_fingerprint("llm_consensus", "llm_consensus"),
})


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

# Category-adaptive Bayesian priors — tuned per tool category
CATEGORY_PRIORS: dict[str, tuple[float, float]] = {
    "Payment APIs": (8.0, 1.0),       # ~89% — payment providers are generally reliable
    "Email APIs": (7.0, 1.0),         # ~87%
    "Cloud Storage": (8.0, 1.0),      # ~89%
    "LLM APIs": (6.0, 1.5),           # ~80% — LLMs have more variability
    "Search APIs": (6.5, 1.0),        # ~87%
    "Developer Tools": (6.0, 1.0),    # ~86%
    "Communication APIs": (7.0, 1.0), # ~87%
}


def _get_priors(category: str | None) -> tuple[float, float]:
    """Return (alpha, beta) Bayesian priors, adaptive to tool category."""
    if category and category in CATEGORY_PRIORS:
        return CATEGORY_PRIORS[category]
    return (settings.bayesian_alpha_prior, settings.bayesian_beta_prior)


def _nearest_rank(sorted_vals: list[int], p: float) -> int:
    """Nearest-rank percentile — s[ceil(p*n) - 1] clamped to valid range.

    The previous implementation (`s[int(p*n)]`) was off-by-one and collapsed
    to the maximum for small n: for a 20-item list, `int(20*0.95)=19` is the
    last index, so p95 == max, masking tail outliers. The nearest-rank method
    used here matches the definition in RFC 2330 and NIST SP 800-57.
    """
    n = len(sorted_vals)
    idx = max(0, min(n - 1, math.ceil(n * p) - 1))
    return sorted_vals[idx]


def _compute_percentiles(values: list[int]) -> LatencyInfo | None:
    """Compute latency percentiles from a list of values."""
    if not values:
        return None
    s = sorted(values)
    return LatencyInfo(
        avg=round(sum(s) / len(s)),
        p50=round(_nearest_rank(s, 0.50)),
        p95=round(_nearest_rank(s, 0.95)),
        p99=round(_nearest_rank(s, 0.99)),
    )


async def compute_score(
    db: AsyncSession,
    tool: Tool,
    context_hash: str,
    data_pool: str | None = None,
    *,
    eu_only: bool = False,
    gdpr_required: bool = False,
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

    # Cold start — no reports at all. Still honor eu_only/gdpr_required so the
    # caller can surface EU alternatives even for tools we've never seen used.
    if not reports:
        cold = _cold_start_response(now, tool)
        if eu_only or gdpr_required:
            cold.eu_alternatives = await _get_eu_alternatives(
                db, tool, gdpr_required=gdpr_required and not eu_only,
            )
        return cold

    # Determine data source. Synthetic bootstrap reports (seed + LLM consensus +
    # on-demand LLM assessment) use fixed hashed fingerprints, so we compare
    # against that known set rather than a substring match.
    all_llm = all(
        r.reporter_fingerprint in _LLM_SYNTHETIC_FINGERPRINTS for r in reports[:5]
    )
    data_source = "llm_estimated" if all_llm else "empirical"

    # Step 1: Recency-weighted success rate
    weighted_successes = 0.0
    weighted_failures = 0.0
    total_weight = 0.0
    latencies: list[int] = []
    error_counts: dict[str, int] = {}
    reports_7d = 0
    successes_7d = 0
    successes_24h = 0
    reports_24h = 0

    for report in reports:
        created = report.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        # Clamp at zero: if the system clock moved backward or a report is
        # somehow ahead of `now`, a negative age would turn the weight into
        # math.exp(+big) and let one row dominate the weighted average.
        age_days = max(0.0, (now - created).total_seconds() / 86400)
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

        if created >= cutoff_7d:
            reports_7d += 1
            if report.success:
                successes_7d += 1

        if created >= cutoff_24h:
            reports_24h += 1
            if report.success:
                successes_24h += 1

    # Step 2: Bayesian smoothing with category-adaptive priors
    alpha_prior, beta_prior = _get_priors(tool.category)
    alpha = alpha_prior + weighted_successes
    beta = beta_prior + weighted_failures
    reliability = alpha / (alpha + beta)

    # Step 3: Confidence
    n_eff = total_weight
    confidence = 1 - 1 / (1 + math.sqrt(n_eff / 10))

    # Step 4: Failure risk with trend adjustment
    failure_risk = 1 - reliability
    sr_7d = (successes_7d / reports_7d * 100) if reports_7d > 0 else None
    sr_24h = (successes_24h / reports_24h * 100) if reports_24h > 0 else None

    if sr_7d is not None and sr_24h is not None:
        if sr_24h < sr_7d:
            trend_penalty = ((sr_7d - sr_24h) / 100) * 0.5
            failure_risk = min(1.0, failure_risk + trend_penalty)

    risk_label = "low" if failure_risk < 0.15 else "medium" if failure_risk < 0.35 else "high"

    # Step 4b: Trend info
    trend = None
    if sr_7d is not None or sr_24h is not None:
        if sr_7d is not None and sr_24h is not None:
            change = round(sr_24h - sr_7d, 1)
            if change > 2:
                direction = "improving"
            elif change < -2:
                direction = "degrading"
            else:
                direction = "stable"
        else:
            change = None
            direction = "stable"
        trend = TrendInfo(
            direction=direction,
            score_24h=round(sr_24h, 1) if sr_24h is not None else None,
            score_7d=round(sr_7d, 1) if sr_7d is not None else None,
            change_24h=change,
        )

    # Step 5: Success rate strings
    total = len(reports)
    successes_total = sum(1 for r in reports if r.success)
    sr_30d = round(successes_total / total * 100) if total else 0
    success_rate_str = f"{sr_30d}% (last 30 days, {total} calls)"

    # Step 6: Structured pitfalls and mitigations. Tool-specific mitigations
    # (set by the on-demand LLM assessment) win over the generic MITIGATIONS
    # dict, so a payment API gets payment-specific advice instead of the
    # boilerplate "Add request throttling".
    total_failures = sum(1 for r in reports if not r.success)
    sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    tool_mitigations = tool.mitigations_by_category or {}
    pitfalls: list[PitfallDetail] = []
    mitigations: list[str] = []
    for category, count in sorted_errors:
        pct = round(count / total_failures * 100) if total_failures else 0
        mitigation = tool_mitigations.get(category) or MITIGATIONS.get(category)
        pitfalls.append(PitfallDetail(
            category=category,
            percentage=pct,
            count=count,
            mitigation=mitigation,
        ))
        if mitigation:
            mitigations.append(mitigation)

    # Step 7: Latency with percentiles
    avg_latency = round(sum(latencies) / len(latencies)) if latencies else None
    latency_info = _compute_percentiles(latencies)

    # Step 8: Alternatives
    alternatives = await _get_alternatives(db, tool.id)

    # Step 9: Jurisdiction + GDPR flags (from tool metadata)
    juris_category = tool.jurisdiction_category
    juris_fields = _jurisdiction_fields(tool, juris_category)

    # Step 10: EU / GDPR-filtered alternatives on demand. `eu_only` is the
    # stricter filter (EU only) and must override `gdpr_required` (EU +
    # GDPR-adequate) when both are set — otherwise a caller explicitly
    # asking for EU-only would silently get GDPR-adequate results too.
    eu_alts: list[AlternativeTool] = []
    if eu_only or gdpr_required:
        eu_alts = await _get_eu_alternatives(
            db, tool, gdpr_required=gdpr_required and not eu_only,
        )

    return AssessResponse(
        reliability_score=round(reliability * 100, 1),
        confidence=round(confidence, 2),
        data_source=data_source,
        historical_success_rate=success_rate_str,
        predicted_failure_risk=risk_label,
        trend=trend,
        common_pitfalls=pitfalls,
        recommended_mitigations=mitigations,
        top_alternatives=alternatives,
        estimated_latency_ms=avg_latency,
        latency=latency_info,
        last_updated=now,
        **juris_fields,
        eu_alternatives=eu_alts,
    )


def _cold_start_response(now: datetime, tool: Tool | None = None) -> AssessResponse:
    """Response for tools with no data — uses category-adaptive Bayesian prior."""
    tool_category = tool.category if tool else None
    alpha, beta = _get_priors(tool_category)
    reliability = alpha / (alpha + beta)

    if tool is not None:
        juris_fields = _jurisdiction_fields(tool, tool.jurisdiction_category)
    else:
        juris_fields = _jurisdiction_fields(None, None)

    return AssessResponse(
        reliability_score=round(reliability * 100, 1),
        confidence=0.0,
        data_source="bayesian_prior",
        historical_success_rate="No data available",
        predicted_failure_risk="unknown",
        trend=None,
        common_pitfalls=[],
        recommended_mitigations=[],
        top_alternatives=[],
        estimated_latency_ms=None,
        latency=None,
        last_updated=now,
        **juris_fields,
        eu_alternatives=[],
    )


def _jurisdiction_fields(tool: Tool | None, category: str | None) -> dict:
    """Build the jurisdiction-related fields attached to every AssessResponse."""
    if tool is None:
        return {
            "hosting_jurisdiction": None,
            "gdpr_compliant": False,
            "data_residency_risk": "medium",
            "jurisdiction_source": None,
            "jurisdiction_confidence": None,
            "jurisdiction_notes": None,
            "recommended_for": recommended_for(None),
        }
    confidence = tool.jurisdiction_confidence
    return {
        "hosting_jurisdiction": format_hosting_jurisdiction(
            category, tool.hosting_country, tool.hosting_region,
        ),
        "gdpr_compliant": is_gdpr_compliant(category),
        "data_residency_risk": data_residency_risk(category, confidence),
        "jurisdiction_source": tool.jurisdiction_source,
        "jurisdiction_confidence": confidence,
        "jurisdiction_notes": tool.notes,
        "recommended_for": recommended_for(category),
    }


async def _get_eu_alternatives(
    db: AsyncSession,
    tool: Tool,
    *,
    gdpr_required: bool,
    limit: int = 3,
) -> list[AlternativeTool]:
    """Find alternative tools hosted in EU (or GDPR-adequate) jurisdictions.

    **Only trusts high/medium confidence verdicts** — low-confidence EU
    classifications almost always come from IP geolocation hitting a CDN
    edge, so they would mislead callers asking for GDPR-safe alternatives.

    Uses report_count as a cheap proxy for reliability so we don't recompute
    the full score for each candidate.
    """
    allowed = ("EU", "GDPR-adequate") if gdpr_required else ("EU",)
    stmt = (
        select(Tool)
        .where(
            Tool.jurisdiction_category.in_(allowed),
            Tool.jurisdiction_confidence.in_(("high", "medium")),
            Tool.id != tool.id,
            Tool.report_count >= 5,
        )
    )
    if tool.category:
        stmt = stmt.where(Tool.category == tool.category)
    stmt = stmt.order_by(Tool.report_count.desc()).limit(limit)

    results = (await db.execute(stmt)).scalars().all()
    out: list[AlternativeTool] = []
    for peer in results:
        estimated_score = min(95.0, 80.0 + (peer.report_count / 20))
        source_label = peer.jurisdiction_source or "unknown"
        out.append(
            AlternativeTool(
                tool=peer.identifier,
                score=round(estimated_score, 1),
                reason=f"{peer.jurisdiction_category} ({source_label}) in {tool.category or 'same category'}",
            )
        )
    return out


async def _get_alternatives(db: AsyncSession, tool_id) -> list[AlternativeTool]:
    # 1. Check stored alternatives first
    # There's no unique constraint on (tool_id, alternative_tool_id), so
    # re-running seed/import can leave duplicates. Pull more than `limit`
    # rows and dedupe by identifier before truncating, so users don't see
    # the same alternative listed twice.
    result = await db.execute(
        select(Alternative, Tool)
        .join(Tool, Alternative.alternative_tool_id == Tool.id)
        .where(Alternative.tool_id == tool_id)
        .order_by(Alternative.relevance_score.desc())
        .limit(9)
    )
    alternatives: list[AlternativeTool] = []
    seen_identifiers: set[str] = set()
    for alt, alt_tool in result.tuples().all():
        if alt_tool.identifier in seen_identifiers:
            continue
        seen_identifiers.add(alt_tool.identifier)
        alternatives.append(
            AlternativeTool(
                tool=alt_tool.identifier,
                score=round(alt.relevance_score * 100, 1),
                reason=alt.reason or "Alternative provider",
            )
        )
        if len(alternatives) >= 3:
            break

    if alternatives:
        return alternatives

    # 2. Fallback: find top-rated tools in the same category
    tool_result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = tool_result.scalar_one_or_none()
    if not tool or not tool.category:
        return []

    result = await db.execute(
        select(Tool)
        .where(
            Tool.category == tool.category,
            Tool.id != tool_id,
            Tool.report_count >= 10,
        )
        .order_by(Tool.report_count.desc())
        .limit(3)
    )
    category_peers = result.scalars().all()

    for peer in category_peers:
        # Estimate score from report count (higher report count = more established)
        estimated_score = min(95.0, 80.0 + (peer.report_count / 20))
        alternatives.append(
            AlternativeTool(
                tool=peer.identifier,
                score=round(estimated_score, 1),
                reason=f"Top-rated in {tool.category}",
            )
        )

    return alternatives
