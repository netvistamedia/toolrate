from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


_MAX_SAMPLE_PAYLOAD_DEPTH = 6
_MAX_SAMPLE_PAYLOAD_NODES = 1000


def _payload_depth_and_size(obj, _depth=0):
    """Walk a nested structure and return (max_depth, total_node_count).

    Guards against JSON bombs submitted via sample_payload. We never store or
    execute this value — it's only a hint for context-aware scoring — so we
    reject anything pathologically deep or wide before Pydantic materialises
    it further up the stack.
    """
    if _depth > _MAX_SAMPLE_PAYLOAD_DEPTH:
        raise ValueError(f"sample_payload nested deeper than {_MAX_SAMPLE_PAYLOAD_DEPTH} levels")
    count = 1
    if isinstance(obj, dict):
        for v in obj.values():
            count += _payload_depth_and_size(v, _depth + 1)
            if count > _MAX_SAMPLE_PAYLOAD_NODES:
                raise ValueError(f"sample_payload exceeds {_MAX_SAMPLE_PAYLOAD_NODES} total nodes")
    elif isinstance(obj, list):
        for v in obj:
            count += _payload_depth_and_size(v, _depth + 1)
            if count > _MAX_SAMPLE_PAYLOAD_NODES:
                raise ValueError(f"sample_payload exceeds {_MAX_SAMPLE_PAYLOAD_NODES} total nodes")
    return count


class AssessRequest(BaseModel):
    tool_identifier: str = Field(..., max_length=512, description="URL, name, or OpenAPI snippet identifying the tool")
    context: str = Field("", max_length=1024, description="Workflow context for context-bucketed scoring")
    sample_payload: dict | None = Field(None, description="Optional sample payload (not stored). Capped at 6 levels deep / 1000 nodes.")
    eu_only: bool = Field(False, description="If true, surface EU-hosted alternatives in eu_alternatives")
    gdpr_required: bool = Field(False, description="If true, surface EU + GDPR-adequate alternatives in eu_alternatives")
    max_price_per_call: float | None = Field(
        None, ge=0,
        description="Maximum USD the caller will pay per call. Tools above this are flagged with within_budget=false but still returned (no silent filtering).",
    )
    max_monthly_budget: float | None = Field(
        None, ge=0,
        description="Maximum USD spend per month. Combined with expected_calls_per_month to evaluate the within_budget flag.",
    )
    expected_calls_per_month: int | None = Field(
        None, ge=0,
        description="Expected call volume. Used for estimated_monthly_cost projection and free-tier-aware effective cost.",
    )
    budget_strategy: Literal["reliability_first", "balanced", "cost_first"] = Field(
        "reliability_first",
        description="How to trade reliability against cost when computing cost_adjusted_score. Weights: reliability_first 0.80/0.20, balanced 0.55/0.45, cost_first 0.25/0.75.",
    )

    @field_validator("sample_payload")
    @classmethod
    def _validate_sample_payload(cls, v):
        if v is None:
            return v
        _payload_depth_and_size(v)
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tool_identifier": "https://api.stripe.com/v1/charges",
                    "context": "high-value payment processing for e-commerce checkout",
                },
                {
                    "tool_identifier": "https://api.openai.com/v1/chat/completions",
                    "context": "customer support chatbot",
                },
            ]
        }
    }


class AlternativeTool(BaseModel):
    tool: str = Field(..., description="Tool identifier")
    score: float = Field(..., description="Reliability score of the alternative (0-100)")
    reason: str = Field(..., description="Why this is a good alternative")
    price_per_call: float | None = Field(None, description="USD cost per call for this alternative (null when pricing is unknown)")
    within_budget: bool | None = Field(None, description="True when this alternative fits the caller's budget (null when no budget cap was set or pricing is unknown)")


class PitfallDetail(BaseModel):
    category: str = Field(..., description="Error category (e.g. timeout, rate_limit)")
    percentage: int = Field(..., description="Percentage of total failures")
    count: int = Field(..., description="Absolute number of occurrences")
    mitigation: str | None = Field(None, description="Recommended action to mitigate this failure")


class TrendInfo(BaseModel):
    direction: str = Field(..., description="Trend direction: improving, stable, or degrading")
    score_24h: float | None = Field(None, description="Success rate over the last 24 hours (0-100)")
    score_7d: float | None = Field(None, description="Success rate over the last 7 days (0-100)")
    change_24h: float | None = Field(None, description="Score change vs 7-day baseline (negative = degrading)")


class LatencyInfo(BaseModel):
    avg: float | None = Field(None, description="Average latency in ms")
    p50: float | None = Field(None, description="Median (50th percentile) latency in ms")
    p95: float | None = Field(None, description="95th percentile latency in ms")
    p99: float | None = Field(None, description="99th percentile latency in ms")


class AssessResponse(BaseModel):
    reliability_score: float = Field(..., ge=0, le=100, description="Reliability score (0-100)")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in the score (0-1), based on data volume")
    data_source: str = Field(..., description="Where this score comes from: empirical, llm_estimated, or bayesian_prior")
    historical_success_rate: str = Field(..., description="Human-readable success rate summary")
    predicted_failure_risk: str = Field(..., description="Risk level: low, medium, high, or unknown")
    trend: TrendInfo | None = Field(None, description="Score trend over time (null for cold start)")
    common_pitfalls: list[PitfallDetail] = Field(..., description="Most common failure categories with counts and mitigations")
    recommended_mitigations: list[str] = Field(..., description="Actionable steps to reduce failure risk")
    top_alternatives: list[AlternativeTool] = Field(..., description="Up to 3 alternative tools with their scores")
    estimated_latency_ms: float | None = Field(None, description="Average latency in milliseconds (deprecated, use latency)")
    latency: LatencyInfo | None = Field(None, description="Latency percentiles (avg, P50, P95, P99)")
    last_updated: datetime = Field(..., description="When this score was last computed")
    hosting_jurisdiction: str | None = Field(None, description="Human-readable hosting jurisdiction, e.g. 'EU (Germany - Frankfurt)'")
    gdpr_compliant: bool = Field(False, description="True for EU and GDPR-adequate jurisdictions")
    data_residency_risk: str = Field("medium", description="GDPR residency risk: none, low, medium, or high")
    jurisdiction_source: str | None = Field(None, description="Where the jurisdiction verdict came from: manual, whois, ip_geolocation, or cdn_detected")
    jurisdiction_confidence: str | None = Field(None, description="Trustworthiness of the jurisdiction verdict: high, medium, or low")
    jurisdiction_notes: str | None = Field(None, description="Short explanation of the jurisdiction assignment")
    recommended_for: list[str] = Field(default_factory=list, description="Workflow tags this tool is suited for, e.g. 'eu_companies', 'gdpr_strict_workflows'")
    eu_alternatives: list[AlternativeTool] = Field(default_factory=list, description="EU-hosted (or GDPR-adequate) alternatives when eu_only/gdpr_required is set")
    price_per_call: float | None = Field(None, description="USD cost per call for this tool (null when pricing is unknown)")
    pricing_model: str | None = Field(None, description="Pricing model: per_call, per_token, flat_monthly, freemium, or unknown")
    cost_adjusted_score: float | None = Field(None, ge=0, le=100, description="Combined 0-100 score weighting reliability against cost, normalized against the category median and weighted by budget_strategy")
    estimated_monthly_cost: float | None = Field(None, description="Projected USD spend per month at expected_calls_per_month (null when not set)")
    within_budget: bool | None = Field(None, description="True when this tool fits the caller's budget (null when no budget cap was set or pricing is unknown)")
    budget_explanation: str | None = Field(None, description="Human-readable explanation comparing the tool's cost to the caller's budget constraints")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "reliability_score": 94.2,
                    "confidence": 0.87,
                    "data_source": "empirical",
                    "historical_success_rate": "89% (last 30 days, 12k calls)",
                    "predicted_failure_risk": "low",
                    "trend": {
                        "direction": "stable",
                        "score_24h": 91.0,
                        "score_7d": 89.0,
                        "change_24h": 2.0,
                    },
                    "common_pitfalls": [
                        {"category": "timeout", "percentage": 8, "count": 120, "mitigation": "Increase timeout to 30s; implement retry with exponential backoff"},
                        {"category": "rate_limit", "percentage": 3, "count": 45, "mitigation": "Add request throttling; use credential rotation if available"},
                    ],
                    "recommended_mitigations": [
                        "Increase timeout to 30s; implement retry with exponential backoff",
                        "Add request throttling; use credential rotation if available",
                    ],
                    "top_alternatives": [
                        {"tool": "https://api.lemonsqueezy.com/v1/checkouts", "score": 97.1, "reason": "Alternative provider"},
                    ],
                    "estimated_latency_ms": 420,
                    "latency": {"avg": 420, "p50": 380, "p95": 890, "p99": 1200},
                    "last_updated": "2026-04-11T09:05:00Z",
                }
            ]
        }
    }
