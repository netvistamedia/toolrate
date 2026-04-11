from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    tool_identifier: str = Field(..., max_length=512, description="URL or name of the tool that was called")
    success: bool = Field(..., description="Whether the tool call succeeded")
    error_category: str | None = Field(None, max_length=128, description="Error type: timeout, rate_limit, auth_failure, validation_error, server_error, connection_error, not_found, permission_denied")
    latency_ms: int | None = Field(None, ge=0, le=300000, description="Execution latency in milliseconds")
    context: str = Field("", max_length=1024, description="Workflow context (hashed for privacy)")
    session_id: str | None = Field(None, max_length=64, description="Groups related tool calls in the same workflow. Use a UUID or random string per agent session.")
    attempt_number: int | None = Field(None, ge=1, le=20, description="Which attempt is this? 1 = first try, 2 = fallback after first tool failed, etc.")
    previous_tool: str | None = Field(None, max_length=512, description="Tool identifier that was tried before this one (if this is a fallback)")

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
                    "tool_identifier": "https://api.resend.com/emails",
                    "success": True,
                    "latency_ms": 180,
                    "context": "order confirmation email",
                    "session_id": "agent-session-abc123",
                    "attempt_number": 2,
                    "previous_tool": "https://api.sendgrid.com/v3/mail/send",
                },
            ]
        }
    }


class ReportResponse(BaseModel):
    status: str = Field("accepted", description="Always 'accepted' on success")
    tool_id: str = Field(..., description="Internal tool UUID")
