from datetime import datetime

from pydantic import BaseModel, Field


class AssessRequest(BaseModel):
    tool_identifier: str = Field(..., max_length=512, description="URL, name, or OpenAPI snippet identifying the tool")
    context: str = Field("", max_length=1024, description="Workflow context for context-bucketed scoring")
    sample_payload: dict | None = Field(None, description="Optional sample payload (not stored)")
    eu_only: bool = Field(False, description="If true, surface EU-hosted alternatives in eu_alternatives")
    gdpr_required: bool = Field(False, description="If true, surface EU + GDPR-adequate alternatives in eu_alternatives")

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
