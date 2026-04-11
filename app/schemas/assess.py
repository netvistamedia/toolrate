from datetime import datetime

from pydantic import BaseModel, Field


class AssessRequest(BaseModel):
    tool_identifier: str = Field(..., max_length=512, description="URL, name, or OpenAPI snippet identifying the tool")
    context: str = Field("", max_length=1024, description="Workflow context for context-bucketed scoring")
    sample_payload: dict | None = Field(None, description="Optional sample payload (not stored)")

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


class AssessResponse(BaseModel):
    reliability_score: float = Field(..., ge=0, le=100, description="Reliability score (0-100)")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in the score (0-1), based on data volume")
    historical_success_rate: str = Field(..., description="Human-readable success rate summary")
    predicted_failure_risk: str = Field(..., description="Risk level: low, medium, high, or unknown")
    common_pitfalls: list[str] = Field(..., description="Most common failure categories with percentages")
    recommended_mitigations: list[str] = Field(..., description="Actionable steps to reduce failure risk")
    top_alternatives: list[AlternativeTool] = Field(..., description="Up to 3 alternative tools with their scores")
    estimated_latency_ms: float | None = Field(None, description="Average latency in milliseconds")
    last_updated: datetime = Field(..., description="When this score was last computed")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "reliability_score": 94.2,
                    "confidence": 0.87,
                    "historical_success_rate": "89% (last 30 days, 12k calls)",
                    "predicted_failure_risk": "low",
                    "common_pitfalls": ["timeout (8% of failures)", "rate_limit (3% of failures)"],
                    "recommended_mitigations": [
                        "Increase timeout to 30s; implement retry with exponential backoff",
                        "Add request throttling; use credential rotation if available",
                    ],
                    "top_alternatives": [
                        {"tool": "https://api.lemonsqueezy.com/v1/checkouts", "score": 97.1, "reason": "Alternative provider"},
                    ],
                    "estimated_latency_ms": 420,
                    "last_updated": "2026-04-11T09:05:00Z",
                }
            ]
        }
    }
