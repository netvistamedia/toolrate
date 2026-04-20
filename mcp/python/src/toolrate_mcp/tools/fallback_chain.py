"""``toolrate_fallback_chain`` — discover what agents switch to when a tool fails."""
from __future__ import annotations

import json
from typing import Annotated, Any, Optional

from pydantic import Field

from ..client import api_request
from ..errors import raise_tool_error

NAME = "toolrate_fallback_chain"

DESCRIPTION = "\n".join(
    [
        "Given a tool identifier, return the tools that real agents actually switched to after this one failed — ranked by success rate in the fallback position.",
        "",
        "Use this when toolrate_assess flagged the primary tool as risky, or when a live call just failed and you need a fallback.",
    ]
)


async def handler(
    tool_identifier: Annotated[str, Field(min_length=1, max_length=512, description="The tool to find fallbacks for.")],
    limit: Annotated[Optional[int], Field(default=None, ge=1, le=20, description="Max results (default 5).")] = None,
) -> str:
    try:
        body, rate_limit = await api_request(
            method="GET",
            path="/v1/discover/fallback-chain",
            query={"tool_identifier": tool_identifier, "limit": limit},
        )
    except Exception as e:
        raise_tool_error(e)

    result: dict[str, Any] = {**body}
    if rate_limit is not None:
        result["_meta"] = {"rate_limit": rate_limit}
    return json.dumps(result, indent=2)
