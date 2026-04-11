from datetime import datetime

from pydantic import BaseModel, Field


class AssessRequest(BaseModel):
    tool_identifier: str = Field(..., max_length=512, description="URL, name, or OpenAPI snippet identifying the tool")
    context: str = Field("", max_length=1024, description="Workflow context for context-bucketed scoring")
    sample_payload: dict | None = Field(None, description="Optional sample payload (not stored)")


class AlternativeTool(BaseModel):
    tool: str
    score: float
    reason: str


class AssessResponse(BaseModel):
    reliability_score: float = Field(..., ge=0, le=100)
    confidence: float = Field(..., ge=0, le=1)
    historical_success_rate: str
    predicted_failure_risk: str
    common_pitfalls: list[str]
    recommended_mitigations: list[str]
    top_alternatives: list[AlternativeTool]
    estimated_latency_ms: float | None
    last_updated: datetime
