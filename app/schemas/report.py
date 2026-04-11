from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    tool_identifier: str = Field(..., max_length=512, description="URL or name of the tool that was called")
    success: bool = Field(..., description="Whether the tool call succeeded")
    error_category: str | None = Field(None, max_length=128, description="Error type: timeout, rate_limit, auth_failure, validation_error, server_error, connection_error, not_found, permission_denied")
    latency_ms: int | None = Field(None, ge=0, le=300000, description="Execution latency in milliseconds")
    context: str = Field("", max_length=1024, description="Workflow context (hashed for privacy)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tool_identifier": "https://api.stripe.com/v1/charges",
                    "success": True,
                    "latency_ms": 420,
                    "context": "e-commerce checkout",
                },
                {
                    "tool_identifier": "https://api.openai.com/v1/chat/completions",
                    "success": False,
                    "error_category": "timeout",
                    "latency_ms": 30000,
                    "context": "customer support chatbot",
                },
            ]
        }
    }


class ReportResponse(BaseModel):
    status: str = Field("accepted", description="Always 'accepted' on success")
    tool_id: str = Field(..., description="Internal tool UUID")
