"""``toolrate_report`` — outcome reporter."""
from __future__ import annotations

import json
from typing import Annotated, Any, Literal, Optional

from pydantic import Field

from ..client import api_request
from ..errors import raise_tool_error

NAME = "toolrate_report"

DESCRIPTION = "\n".join(
    [
        "Tell ToolRate what happened after you invoked a third-party tool/API. This is how the reliability scores improve.",
        "",
        "Guard pattern: call this AFTER every third-party tool call you make. Report success=true on success; on failure, set success=false and pass error_category.",
        "",
        "When chaining attempts, set attempt_number (2 = first fallback, 3 = second, …) and previous_tool — this builds the fallback-chain analytics that power toolrate_fallback_chain.",
    ]
)

ErrorCategory = Literal[
    "timeout",
    "rate_limit",
    "auth_failure",
    "validation_error",
    "server_error",
    "connection_error",
    "not_found",
    "permission_denied",
]


async def handler(
    tool_identifier: Annotated[str, Field(min_length=1, max_length=512, description="Tool identifier that was called.")],
    success: Annotated[bool, Field(description="Whether the call succeeded.")],
    error_category: Annotated[
        Optional[ErrorCategory],
        Field(default=None, description="Failure category. Required when success=false to be useful."),
    ] = None,
    latency_ms: Annotated[
        Optional[int],
        Field(default=None, ge=1, le=300_000, description="How long the call took in milliseconds."),
    ] = None,
    context: Annotated[
        Optional[str],
        Field(default=None, max_length=1024, description="Workflow context, hashed for privacy."),
    ] = None,
    session_id: Annotated[
        Optional[str],
        Field(default=None, max_length=64, description="UUID grouping related calls in one workflow (for journey analytics)."),
    ] = None,
    attempt_number: Annotated[
        Optional[int],
        Field(default=None, ge=1, le=20, description="Which attempt this was. 1 = first try, 2 = first fallback, etc."),
    ] = None,
    previous_tool: Annotated[
        Optional[str],
        Field(default=None, max_length=512, description="Tool identifier that was tried before this one (for fallback chains)."),
    ] = None,
) -> str:
    try:
        body, rate_limit = await api_request(
            method="POST",
            path="/v1/report",
            body={
                "tool_identifier": tool_identifier,
                "success": success,
                "error_category": error_category,
                "latency_ms": latency_ms,
                "context": context,
                "session_id": session_id,
                "attempt_number": attempt_number,
                "previous_tool": previous_tool,
            },
        )
    except Exception as e:
        raise_tool_error(e)

    result: dict[str, Any] = {**body}
    if rate_limit is not None:
        result["_meta"] = {"rate_limit": rate_limit}
    return json.dumps(result, indent=2)
