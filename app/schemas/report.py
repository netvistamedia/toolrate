from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    tool_identifier: str = Field(..., max_length=512)
    success: bool
    error_category: str | None = Field(None, max_length=128)
    latency_ms: int | None = Field(None, ge=0, le=300000)
    context: str = Field("", max_length=1024)


class ReportResponse(BaseModel):
    status: str = "accepted"
    tool_id: str
