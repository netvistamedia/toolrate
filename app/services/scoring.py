import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.error_categories import is_sdk_skip
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

# Category-adaptive Bayesian priors — tuned per canonical tool category.
# Keys must match the canonical Title-Case names in the DB (see the category
# merge run on 2026-04-14). Categories absent here fall through to the
# default (settings.bayesian_alpha_prior / beta_prior).
CATEGORY_PRIORS: dict[str, tuple[float, float]] = {
    "Payment APIs":           (8.0, 1.0),  # ~89% — payment providers are generally reliable
    "Email APIs":             (7.0, 1.0),  # ~87%
    "Cloud Storage":          (8.0, 1.0),  # ~89%
    "LLM APIs":               (6.0, 1.5),  # ~80% — LLMs have more variability
    "Search APIs":            (6.5, 1.0),  # ~87%
    "Developer Tools":        (6.0, 1.0),  # ~86%
    "Messaging":              (7.0, 1.0),  # ~87% — SMS/queues/event buses are mature infra
    "Databases & BaaS":       (7.5, 1.0),  # ~88%
    "Vector Databases":       (6.5, 1.0),  # ~87% — newer category, still mostly reliable
    "Auth & Identity":        (7.5, 1.0),  # ~88%
    "Monitoring & Analytics": (7.0, 1.0),  # ~87%
    "CRM & Productivity":     (6.5, 1.0),  # ~87%
    "Maps & Location":        (7.0, 1.0),  # ~87%
    "Web Scraping":           (5.0, 2.0),  # ~71% — scrapers are inherently flaky
    "Browser Automation":     (5.0, 2.0),  # ~71% — headless browsers are notoriously brittle
    "Image/Media Generation": (6.0, 1.5),  # ~80% — creative AI has variable quality/uptime
    "Code Execution":         (6.0, 1.5),  # ~80% — sandbox failures are common
    "E-commerce":             (7.0, 1.0),  # ~87%
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


# ---------------------------------------------------------------------------
# Cost-aware scoring
#
# These helpers turn the `pricing` JSON on a Tool row into the cost fields on
# an AssessResponse. The single public entry point is `finalize_response`,
# which is called by compute_score (for fresh scores) and by /v1/assess (for
# cached scores). Keeping both paths funnelling through one helper means a
# request returning a cached score still sees budget math computed against
# ITS request parameters, not the parameters of whichever request first
# populated the cache.
# ---------------------------------------------------------------------------

# Strategy weights are 3-tuples (reliability, cost, latency). The two-axis
# strategies carry a trailing 0.0 for latency so the formula is uniform.
# The four strategies are:
#
#   reliability_first  (0.80, 0.20, 0.00) — locked in 2026-04-15
#   balanced           (0.55, 0.45, 0.00) — locked in 2026-04-15
#   cost_first         (0.25, 0.75, 0.00) — locked in 2026-04-15
#   speed_first        (0.35, 0.45, 0.20) — shipped with the LLM router feature
#
# Rows must sum to 1.0. The original three weights are preserved byte-for-byte
# so existing test expectations and cached cost_adjusted_score values don't
# move. speed_first is the one strategy that consumes the third axis — the
# others would need latency data on every priced tool before flipping it on.
_STRATEGY_WEIGHTS: dict[str, tuple[float, float, float]] = {
    "reliability_first": (0.80, 0.20, 0.00),
    "balanced":          (0.55, 0.45, 0.00),
    "cost_first":        (0.25, 0.75, 0.00),
    "speed_first":       (0.35, 0.45, 0.20),
}

# Category-median prices AND latencies are essentially static within a
# 15-minute window, so we cache them in-process to avoid extra DB round-trips
# on every assess call. Bounded by the number of distinct categories (~20)
# times two axes, so the memory footprint is trivial. Per-process; no Redis.
_CATEGORY_MEDIAN_CACHE: dict[str, tuple[float | None, datetime]] = {}
_CATEGORY_LATENCY_MEDIAN_CACHE: dict[str, tuple[float | None, datetime]] = {}
_CATEGORY_MEDIAN_TTL_SEC = 900

# Task-complexity rank so _pick_recommended_model can filter the catalog —
# higher rank means harder task. A model with tier >= target_rank is
# considered "capable enough" for the task; the strategy decides which of
# the capable ones wins.
_COMPLEXITY_RANK: dict[str, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "very_high": 3,
}

# Default input/output token split when we have per-million pricing and
# expected_tokens but no explicit ratio. A 30/70 split matches typical LLM
# chat workloads (short user prompt, longer model reply). Callers who care
# about exact math can pre-compute their own effective cost and pass it in
# via the manual seed instead.
_DEFAULT_INPUT_RATIO = 0.30


def _per_call_cost_for_tokens(
    pricing: dict, expected_tokens: int | None, input_ratio: float = _DEFAULT_INPUT_RATIO,
) -> float | None:
    """Exact $/call from per-million-token pricing when the ingredients exist.

    Returns None when any input is missing so callers can fall through to
    the blended ``typical_usd_per_call`` path. Split is 30/70 input/output
    by default — see ``_DEFAULT_INPUT_RATIO``.
    """
    if not expected_tokens or expected_tokens <= 0:
        return None
    in_price = pricing.get("usd_per_million_input_tokens")
    out_price = pricing.get("usd_per_million_output_tokens")
    if in_price is None or out_price is None:
        return None
    try:
        in_p = max(0.0, float(in_price))
        out_p = max(0.0, float(out_price))
    except (TypeError, ValueError):
        return None
    input_tokens = expected_tokens * input_ratio
    output_tokens = expected_tokens * (1.0 - input_ratio)
    return round(((input_tokens * in_p) + (output_tokens * out_p)) / 1_000_000, 10)


def _effective_cost(
    pricing: dict | None,
    expected_calls_per_month: int | None,
    expected_tokens: int | None = None,
) -> float | None:
    """Return the steady-state $/call implied by a pricing dict.

    Resolution order:

    1. **Exact per-token math** when ``expected_tokens`` is set AND the pricing
       carries ``usd_per_million_input_tokens`` + ``usd_per_million_output_tokens``.
       This is how the LLM router gets precise numbers for per-token APIs.
    2. ``base_usd_per_call`` (per_call / freemium tools).
    3. ``typical_usd_per_call`` (per_token fallback or transactional APIs).

    Honors the free tier when we know the caller's expected volume — a caller
    asking about 2000 calls/mo against a 3000/mo free tier gets $0 back.

    Returns None when the pricing dict is missing or carries no usable price.
    """
    if not pricing:
        return None

    # 1. Exact per-token math — preferred when available
    token_cost = _per_call_cost_for_tokens(pricing, expected_tokens)
    if token_cost is not None:
        raw_price = token_cost
    else:
        # 2/3. Blended base/typical fallback (existing path)
        base = pricing.get("base_usd_per_call")
        typical = pricing.get("typical_usd_per_call")
        raw = base if base is not None else typical
        if raw is None:
            return None
        try:
            raw_price = max(0.0, float(raw))
        except (TypeError, ValueError):
            return None

    free_tier = pricing.get("free_tier_per_month")
    if (
        expected_calls_per_month
        and free_tier
        and expected_calls_per_month > 0
    ):
        try:
            free_tier_int = int(free_tier)
        except (TypeError, ValueError):
            free_tier_int = 0
        if free_tier_int > 0:
            billable = max(0, expected_calls_per_month - free_tier_int)
            if billable == 0:
                return 0.0
            return round((billable * raw_price) / expected_calls_per_month, 8)

    return round(raw_price, 8)


def _cost_adjusted_score(
    reliability_score: float,
    effective_cost: float,
    category_median: float | None,
    strategy: str,
    *,
    latency_ms: float | None = None,
    category_median_latency_ms: float | None = None,
) -> float:
    """Combined 0-100 score weighting reliability / cost / latency.

    Each axis is normalized independently:

    - **Cost**: ``cost_norm = min(1, effective_cost / category_median)``.
      Below the median is cheaper-than-peers; above is capped at the median.
    - **Latency**: same shape, against ``category_median_latency_ms``. Only
      consumed when the strategy has a non-zero latency weight AND the tool
      carries a latency signal (either an observed median or a stored
      ``typical_latency_ms`` in its pricing JSON).

    Strategy weights live in ``_STRATEGY_WEIGHTS`` as 3-tuples. If the
    caller picks ``speed_first`` but we have no latency data, the latency
    weight is redistributed to reliability — better to degrade gracefully
    than return an artificially-low score for tools we simply lack data on.
    """
    if category_median and category_median > 0:
        cost_norm = min(1.0, effective_cost / category_median)
    elif effective_cost <= 0:
        # Peer group is all-free and so is this tool — no cost penalty.
        cost_norm = 0.0
    else:
        # Peer group is all-free but this tool isn't — full cost penalty.
        cost_norm = 1.0

    weights = _STRATEGY_WEIGHTS.get(strategy, _STRATEGY_WEIGHTS["reliability_first"])
    w_rel, w_cost, w_lat = weights

    cost_side = 100.0 - (cost_norm * 100.0)

    if (
        w_lat > 0
        and latency_ms is not None
        and category_median_latency_ms is not None
        and category_median_latency_ms > 0
    ):
        lat_norm = min(1.0, max(0.0, latency_ms / category_median_latency_ms))
        lat_side = 100.0 - (lat_norm * 100.0)
    else:
        # No latency signal — fold the latency weight back into reliability
        # so the score still sums to 100% of reliability+cost contributions.
        w_rel = w_rel + w_lat
        w_lat = 0.0
        lat_side = 0.0

    cost_adjusted = (w_rel * reliability_score) + (w_cost * cost_side) + (w_lat * lat_side)
    return round(max(0.0, min(100.0, cost_adjusted)), 1)


def _pick_recommended_model(
    pricing: dict | None,
    task_complexity: str,
    budget_strategy: str,
) -> tuple[str | None, dict | None]:
    """Pick the best-fit model inside a provider for the caller's task.

    Two-path resolution:

    - **(A) Model catalog** — when the pricing JSON carries a ``models`` list,
      filter down to models whose ``tier`` is at least the caller's
      ``task_complexity``, then rank by strategy:

      * ``cost_first`` → cheapest (sum of per-M in/out prices) that qualifies
      * ``speed_first`` → lowest ``typical_latency_ms`` that qualifies
      * ``reliability_first`` → highest-tier model available (hedge toward power)
      * ``balanced`` → combined cost + latency penalty, lower is better

      Returns ``(model.name, model_dict)``.

    - **(B) String hint fallback** — when no catalog is present, return the
      provider-level ``recommended_model`` string verbatim (or None).

    Returning a (name, dict) tuple lets the caller also read the selected
    model's per-token prices for exact cost math, without re-querying the
    pricing JSON.
    """
    if not pricing:
        return None, None

    simple_hint = pricing.get("recommended_model")
    models = pricing.get("models")
    if not models or not isinstance(models, list):
        return simple_hint, None

    target_rank = _COMPLEXITY_RANK.get(task_complexity, _COMPLEXITY_RANK["medium"])
    capable = [
        m for m in models
        if isinstance(m, dict)
        and _COMPLEXITY_RANK.get(str(m.get("tier", "medium")), _COMPLEXITY_RANK["medium"])
        >= target_rank
    ]
    # If no catalog entry is capable-enough, widen to the full catalog rather
    # than returning nothing — the caller still gets a defensible choice.
    pool = capable if capable else [m for m in models if isinstance(m, dict)]
    if not pool:
        return simple_hint, None

    def _model_cost(m: dict) -> float:
        in_p = m.get("usd_per_million_input_tokens") or 0.0
        out_p = m.get("usd_per_million_output_tokens") or 0.0
        try:
            return float(in_p) + float(out_p)
        except (TypeError, ValueError):
            return 0.0

    def _model_latency(m: dict) -> float:
        v = m.get("typical_latency_ms")
        try:
            return float(v) if v is not None else float("inf")
        except (TypeError, ValueError):
            return float("inf")

    def _model_tier(m: dict) -> int:
        return _COMPLEXITY_RANK.get(
            str(m.get("tier", "medium")), _COMPLEXITY_RANK["medium"]
        )

    if budget_strategy == "cost_first":
        pool.sort(key=lambda m: (_model_cost(m), -_model_tier(m)))
    elif budget_strategy == "speed_first":
        pool.sort(key=lambda m: (_model_latency(m), _model_cost(m)))
    elif budget_strategy == "reliability_first":
        # Hedge toward the most capable model available — matches the
        # strategy semantics ("pay a bit more for a safer bet").
        pool.sort(key=lambda m: (-_model_tier(m), _model_cost(m)))
    else:  # balanced
        # Rough combined penalty — scaled so cost and latency weigh
        # comparably for typical LLM numbers (pennies vs. seconds).
        def _balanced_key(m: dict) -> float:
            return _model_cost(m) * 5.0 + _model_latency(m) / 1000.0 - _model_tier(m) * 2.0
        pool.sort(key=_balanced_key)

    picked = pool[0]
    return picked.get("name") or simple_hint, picked


def _build_reasoning(
    tool: Tool | None,
    response: AssessResponse,
    *,
    task_complexity: str,
    budget_strategy: str,
    recommended_model: str | None,
    within_budget: bool | None,
    latency_ms: float | None,
) -> str:
    """Human-readable explanation of the routing decision.

    This is the string developers see when they print ``response.reasoning``.
    It should be concise but informative — name the tool, the score, the
    strategy, the task complexity, the cost, and the budget fit. Never use
    raw identifiers when a display name exists.
    """
    name = (tool.display_name or tool.identifier) if tool is not None else "This tool"
    parts: list[str] = []

    parts.append(
        f"{name} scored {response.reliability_score}/100 for reliability "
        f"({response.predicted_failure_risk} risk)."
    )

    if recommended_model:
        parts.append(f"Recommended model: {recommended_model}.")

    cost_bits: list[str] = []
    if response.price_per_call is not None:
        cost_bits.append(f"${response.price_per_call:.4f}/call")
    if response.estimated_monthly_cost is not None:
        cost_bits.append(f"${response.estimated_monthly_cost:.2f}/mo projected")
    if cost_bits:
        parts.append("Cost: " + ", ".join(cost_bits) + ".")

    if latency_ms is not None:
        parts.append(f"Typical latency ~{int(latency_ms)}ms.")

    strategy_label = {
        "reliability_first": "reliability-first (80% reliability / 20% cost)",
        "balanced": "balanced (55% reliability / 45% cost)",
        "cost_first": "cost-first (25% reliability / 75% cost)",
        "speed_first": "speed-first (35% reliability / 45% cost / 20% latency)",
    }.get(budget_strategy, budget_strategy)
    parts.append(
        f"Strategy: {strategy_label}; task complexity: {task_complexity}."
    )

    if within_budget is False:
        parts.append("Over budget — flagged but returned for transparency.")
    elif within_budget is True:
        parts.append("Fits within your budget.")

    return " ".join(parts)


def _is_within_budget(
    effective_cost: float,
    max_price_per_call: float | None,
    max_monthly_budget: float | None,
    expected_calls_per_month: int | None,
) -> bool:
    """True when the effective cost satisfies every applicable budget cap."""
    if max_price_per_call is not None and effective_cost > max_price_per_call:
        return False
    if (
        max_monthly_budget is not None
        and expected_calls_per_month
        and expected_calls_per_month > 0
    ):
        if effective_cost * expected_calls_per_month > max_monthly_budget:
            return False
    return True


def _budget_explanation(
    tool: Tool | None,
    effective_cost: float,
    max_price_per_call: float | None,
    max_monthly_budget: float | None,
    expected_calls_per_month: int | None,
    within_budget: bool,
) -> str:
    """Human-readable comparison of tool cost against the caller's budget."""
    display = (
        (tool.display_name or tool.identifier) if tool is not None else "This tool"
    )

    if within_budget:
        parts: list[str] = []
        if max_price_per_call is not None:
            parts.append(
                f"${effective_cost:.4f}/call within ${max_price_per_call:.4f} cap"
            )
        if (
            max_monthly_budget is not None
            and expected_calls_per_month
            and expected_calls_per_month > 0
        ):
            monthly = effective_cost * expected_calls_per_month
            parts.append(
                f"${monthly:.2f}/mo within ${max_monthly_budget:.2f} budget"
            )
        if parts:
            return f"{display} fits comfortably — " + "; ".join(parts) + "."
        return f"{display} fits within budget."

    reasons: list[str] = []
    if max_price_per_call is not None and effective_cost > max_price_per_call:
        over = effective_cost - max_price_per_call
        reasons.append(
            f"${effective_cost:.4f}/call exceeds your ${max_price_per_call:.4f} "
            f"max_price_per_call by ${over:.4f}"
        )
    if (
        max_monthly_budget is not None
        and expected_calls_per_month
        and expected_calls_per_month > 0
    ):
        monthly = effective_cost * expected_calls_per_month
        if monthly > max_monthly_budget:
            over = monthly - max_monthly_budget
            reasons.append(
                f"${monthly:.2f}/mo at {expected_calls_per_month} calls "
                f"exceeds your ${max_monthly_budget:.2f} monthly budget "
                f"by ${over:.2f}"
            )
    if reasons:
        return f"{display} exceeds your budget: " + "; ".join(reasons) + "."
    return f"{display} is flagged as over budget."


async def _category_median_cost(
    db: AsyncSession, category: str | None
) -> float | None:
    """Median effective $/call across priced peers in a category.

    Falls back to the global median (all priced tools, any category) when a
    category has fewer than 3 priced peers. This mirrors the thin-sample
    heuristic in _get_eu_alternatives: below 3 peers the median is noise
    and over-normalises the cost penalty.
    """
    cache_key = category or "__global__"
    now = datetime.now(timezone.utc)
    cached = _CATEGORY_MEDIAN_CACHE.get(cache_key)
    if cached is not None:
        median, ts = cached
        if (now - ts).total_seconds() < _CATEGORY_MEDIAN_TTL_SEC:
            return median

    stmt = select(Tool).where(Tool.pricing.is_not(None))
    if category:
        stmt = stmt.where(Tool.category == category)
    result = await db.execute(stmt)
    peers = list(result.scalars().all())

    costs: list[float] = []
    for peer in peers:
        c = _effective_cost(peer.pricing, expected_calls_per_month=None)
        if c is not None:
            costs.append(c)

    if len(costs) < 3 and category is not None:
        return await _category_median_cost(db, None)

    if not costs:
        _CATEGORY_MEDIAN_CACHE[cache_key] = (None, now)
        return None

    costs.sort()
    n = len(costs)
    mid = n // 2
    median = costs[mid] if n % 2 else (costs[mid - 1] + costs[mid]) / 2.0
    _CATEGORY_MEDIAN_CACHE[cache_key] = (median, now)
    return median


async def _category_median_latency_ms(
    db: AsyncSession, category: str | None
) -> float | None:
    """Median typical_latency_ms across priced peers in a category.

    Mirrors ``_category_median_cost``: same <3-peers-falls-back-to-global
    heuristic, same 15-minute process-local cache. Only used by
    ``speed_first`` scoring — the other strategies have a zero weight on
    latency so this is never touched on their code path.
    """
    cache_key = category or "__global__"
    now = datetime.now(timezone.utc)
    cached = _CATEGORY_LATENCY_MEDIAN_CACHE.get(cache_key)
    if cached is not None:
        median, ts = cached
        if (now - ts).total_seconds() < _CATEGORY_MEDIAN_TTL_SEC:
            return median

    stmt = select(Tool).where(Tool.pricing.is_not(None))
    if category:
        stmt = stmt.where(Tool.category == category)
    result = await db.execute(stmt)
    peers = list(result.scalars().all())

    latencies: list[float] = []
    for peer in peers:
        lat = _tool_latency_ms(peer.pricing)
        if lat is not None and lat > 0:
            latencies.append(lat)

    if len(latencies) < 3 and category is not None:
        return await _category_median_latency_ms(db, None)

    if not latencies:
        _CATEGORY_LATENCY_MEDIAN_CACHE[cache_key] = (None, now)
        return None

    latencies.sort()
    n = len(latencies)
    mid = n // 2
    median = latencies[mid] if n % 2 else (latencies[mid - 1] + latencies[mid]) / 2.0
    _CATEGORY_LATENCY_MEDIAN_CACHE[cache_key] = (median, now)
    return median


def _tool_latency_ms(pricing: dict | None) -> float | None:
    """Extract the tool's typical latency from its pricing JSON.

    Priority: the provider-level ``typical_latency_ms`` wins. When the
    provider has a model catalog but no top-level latency, we take the
    median of the catalog entries — gives us a reasonable provider-level
    number without forcing every seed to duplicate the value.
    """
    if not pricing:
        return None
    top = pricing.get("typical_latency_ms")
    if top is not None:
        try:
            return max(0.0, float(top))
        except (TypeError, ValueError):
            pass
    models = pricing.get("models")
    if isinstance(models, list) and models:
        latencies: list[float] = []
        for m in models:
            if not isinstance(m, dict):
                continue
            v = m.get("typical_latency_ms")
            if v is None:
                continue
            try:
                latencies.append(float(v))
            except (TypeError, ValueError):
                continue
        if latencies:
            latencies.sort()
            mid = len(latencies) // 2
            if len(latencies) % 2:
                return latencies[mid]
            return (latencies[mid - 1] + latencies[mid]) / 2.0
    return None


def _apply_cost_adjustment(
    response: AssessResponse,
    tool: Tool | None,
    *,
    max_price_per_call: float | None,
    max_monthly_budget: float | None,
    expected_calls_per_month: int | None,
    expected_tokens: int | None,
    task_complexity: str,
    budget_strategy: str,
    category_median: float | None,
    category_median_latency_ms: float | None,
) -> None:
    """Populate cost-aware fields on the response in place.

    Idempotent — safe to call on a response that already has cost fields.
    Always sets ``reasoning`` so callers get a deterministic human-readable
    explanation regardless of whether pricing is known.
    """
    has_budget_param = (
        max_price_per_call is not None
        or max_monthly_budget is not None
        or expected_calls_per_month is not None
        or expected_tokens is not None
    )

    # Always try to surface a recommended_model — useful even when pricing
    # lookup later bails, since the string hint path works on just the
    # ``recommended_model`` key.
    recommended_model: str | None = None
    model_entry: dict | None = None
    if tool is not None and tool.pricing:
        recommended_model, model_entry = _pick_recommended_model(
            tool.pricing, task_complexity, budget_strategy
        )
    response.recommended_model = recommended_model

    if tool is None or not tool.pricing:
        if has_budget_param:
            response.budget_explanation = (
                "No pricing data available for this tool."
            )
        response.reasoning = _build_reasoning(
            tool, response,
            task_complexity=task_complexity,
            budget_strategy=budget_strategy,
            recommended_model=recommended_model,
            within_budget=None,
            latency_ms=None,
        )
        return

    # When a specific model was picked from the catalog, prefer ITS per-token
    # pricing over the provider-level fields so the cost math lines up with
    # the model the caller will actually use. Falls back to provider-level
    # pricing when the model entry lacks per-M prices.
    pricing_for_cost: dict = dict(tool.pricing)
    if model_entry is not None:
        for key in (
            "usd_per_million_input_tokens",
            "usd_per_million_output_tokens",
            "typical_usd_per_call",
            "base_usd_per_call",
        ):
            if model_entry.get(key) is not None:
                pricing_for_cost[key] = model_entry[key]

    effective = _effective_cost(
        pricing_for_cost, expected_calls_per_month, expected_tokens
    )
    if effective is None:
        if has_budget_param:
            response.budget_explanation = (
                "Pricing data is incomplete for this tool."
            )
        response.reasoning = _build_reasoning(
            tool, response,
            task_complexity=task_complexity,
            budget_strategy=budget_strategy,
            recommended_model=recommended_model,
            within_budget=None,
            latency_ms=_tool_latency_ms(tool.pricing),
        )
        return

    response.price_per_call = round(effective, 6)
    response.pricing_model = tool.pricing.get("model")

    # Pick latency for scoring: prefer the specifically-selected model, then
    # the provider-level typical_latency_ms, then the observed response
    # estimated_latency_ms from real execution reports.
    latency_ms: float | None = None
    if model_entry is not None and model_entry.get("typical_latency_ms") is not None:
        try:
            latency_ms = float(model_entry["typical_latency_ms"])
        except (TypeError, ValueError):
            latency_ms = None
    if latency_ms is None:
        latency_ms = _tool_latency_ms(tool.pricing)
    if latency_ms is None and response.estimated_latency_ms is not None:
        try:
            latency_ms = float(response.estimated_latency_ms)
        except (TypeError, ValueError):
            latency_ms = None

    if category_median is not None:
        response.cost_adjusted_score = _cost_adjusted_score(
            response.reliability_score, effective, category_median, budget_strategy,
            latency_ms=latency_ms,
            category_median_latency_ms=category_median_latency_ms,
        )
    else:
        # No peer group to normalise against — fall back to the plain
        # reliability score so callers always have a sortable number.
        response.cost_adjusted_score = round(response.reliability_score, 1)

    if expected_calls_per_month is not None and expected_calls_per_month > 0:
        response.estimated_monthly_cost = round(
            effective * expected_calls_per_month, 4
        )

    has_budget_cap = (
        max_price_per_call is not None or max_monthly_budget is not None
    )
    within: bool | None = None
    if has_budget_cap:
        within = _is_within_budget(
            effective, max_price_per_call, max_monthly_budget,
            expected_calls_per_month,
        )
        response.within_budget = within
        response.budget_explanation = _budget_explanation(
            tool, effective, max_price_per_call, max_monthly_budget,
            expected_calls_per_month, within,
        )
    elif expected_calls_per_month is not None and expected_calls_per_month > 0:
        monthly = effective * expected_calls_per_month
        response.budget_explanation = (
            f"Projected cost: ${monthly:.2f}/mo at {expected_calls_per_month} "
            f"calls/mo (no budget cap set)."
        )

    response.reasoning = _build_reasoning(
        tool, response,
        task_complexity=task_complexity,
        budget_strategy=budget_strategy,
        recommended_model=recommended_model,
        within_budget=within,
        latency_ms=latency_ms,
    )


def _annotate_alternatives_within_budget(
    alternatives: list[AlternativeTool],
    max_price_per_call: float | None,
    max_monthly_budget: float | None,
    expected_calls_per_month: int | None,
) -> None:
    """Set within_budget on each alternative that already has price_per_call."""
    if max_price_per_call is None and max_monthly_budget is None:
        return
    for alt in alternatives:
        if alt.price_per_call is None:
            continue
        alt.within_budget = _is_within_budget(
            alt.price_per_call, max_price_per_call, max_monthly_budget,
            expected_calls_per_month,
        )


async def finalize_response(
    response: AssessResponse,
    db: AsyncSession,
    tool: Tool | None,
    *,
    max_price_per_call: float | None,
    max_monthly_budget: float | None,
    expected_calls_per_month: int | None,
    expected_tokens: int | None = None,
    task_complexity: str = "medium",
    budget_strategy: str,
) -> AssessResponse:
    """Apply the cost-aware augmentation step shared by every return site.

    Compute_score calls this on fresh responses; /v1/assess calls it on
    cached responses. Same request parameters in → same cost fields out,
    cache hit or miss. Thread-safe: mutates the response in place but takes
    no global locks beyond the per-process median cache.
    """
    category_median = (
        await _category_median_cost(db, tool.category) if tool is not None else None
    )
    category_median_latency_ms: float | None = None
    if tool is not None and budget_strategy == "speed_first":
        # speed_first is the only strategy that consumes the latency axis,
        # so we skip the extra DB hit for the other three.
        category_median_latency_ms = await _category_median_latency_ms(
            db, tool.category
        )

    _apply_cost_adjustment(
        response,
        tool,
        max_price_per_call=max_price_per_call,
        max_monthly_budget=max_monthly_budget,
        expected_calls_per_month=expected_calls_per_month,
        expected_tokens=expected_tokens,
        task_complexity=task_complexity,
        budget_strategy=budget_strategy,
        category_median=category_median,
        category_median_latency_ms=category_median_latency_ms,
    )
    _annotate_alternatives_within_budget(
        response.top_alternatives,
        max_price_per_call, max_monthly_budget, expected_calls_per_month,
    )
    _annotate_alternatives_within_budget(
        response.eu_alternatives,
        max_price_per_call, max_monthly_budget, expected_calls_per_month,
    )
    return response


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

    # Drop SDK telemetry markers (skipped_low_score / skipped_over_budget) up
    # front — those rows describe agent decisions, not tool outcomes. Letting
    # them through would inflate the failure count, distort the trend curve,
    # and surface "skipped_low_score" as a top pitfall in the assess response.
    # Fallback-chain analytics live in a separate query path (discovery.py) so
    # the journey signal is not lost.
    reports = [r for r in reports if not is_sdk_skip(r.error_category)]

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

    # Step 1: Recency-weighted success rate. Error counts use the SAME weight
    # so 100 ancient timeouts don't drown out 10 fresh rate_limits in the
    # pitfall ranking — without weighting, the surfaced "common pitfall" was
    # almost always the oldest noisy category instead of the live problem.
    weighted_successes = 0.0
    weighted_failures = 0.0
    total_weight = 0.0
    sum_weight_sq = 0.0
    latencies: list[int] = []
    error_counts: dict[str, float] = {}
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
                error_counts[report.error_category] = (
                    error_counts.get(report.error_category, 0.0) + weight
                )

        total_weight += weight
        sum_weight_sq += weight * weight

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

    # Step 3: Confidence — Kish's effective sample size (Σw)² / Σw².
    # Using ``total_weight`` (the previous formula) is correct ONLY for
    # uniform weights; with a 3.5-day half-life the older reports carry
    # tiny weights, so the naive form was over-reporting confidence by
    # ~13% on a typical sample. Kish's formula collapses to ``n`` when
    # all weights are equal and to a much smaller number when one or two
    # very-recent reports dominate the weighted sum.
    n_eff = (total_weight * total_weight / sum_weight_sq) if sum_weight_sq > 0 else 0.0
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

    # Step 5: Success rate string. Uses the same recency-weighted ratio as
    # ``reliability_score`` (without the Bayesian prior) so the two numbers
    # tell a consistent story — previously this was raw count / total, which
    # diverged from the score by 5-15pp on tools with a noisy backlog.
    total = len(reports)
    sr_30d = (
        round(weighted_successes / total_weight * 100)
        if total_weight > 0
        else 0
    )
    success_rate_str = f"{sr_30d}% (last 30 days, {total} calls)"

    # Step 6: Structured pitfalls and mitigations. Tool-specific mitigations
    # (set by the on-demand LLM assessment) win over the generic MITIGATIONS
    # dict, so a payment API gets payment-specific advice instead of the
    # boilerplate "Add request throttling". Percentages and counts use the
    # recency-weighted totals from step 1 so old failures fade out of the
    # surfaced pitfalls at the same rate as they fade out of the score.
    sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    tool_mitigations = tool.mitigations_by_category or {}
    pitfalls: list[PitfallDetail] = []
    mitigations: list[str] = []
    for category, weighted_count in sorted_errors:
        pct = (
            round(weighted_count / weighted_failures * 100)
            if weighted_failures > 0
            else 0
        )
        mitigation = tool_mitigations.get(category) or MITIGATIONS.get(category)
        pitfalls.append(PitfallDetail(
            category=category,
            percentage=pct,
            count=max(1, round(weighted_count)),
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
                price_per_call=_effective_cost(peer.pricing, None),
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
                price_per_call=_effective_cost(alt_tool.pricing, None),
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
                price_per_call=_effective_cost(peer.pricing, None),
            )
        )

    return alternatives
