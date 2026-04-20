"""``toolrate_hidden_gems`` — surface underrated but reliable tools."""
from __future__ import annotations

import json
from typing import Annotated, Any, Optional

from pydantic import Field

from ..client import api_request
from ..errors import raise_tool_error

NAME = "toolrate_hidden_gems"

DESCRIPTION = "\n".join(
    [
        "Returns tools that have a high success rate in the fallback position but are rarely picked first. Use this to discover lesser-known but reliable APIs in a given category.",
        "",
        "Filter by category — call toolrate_categories first to see the canonical names.",
    ]
)


async def handler(
    category: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=128,
            description="Filter by category (e.g. 'LLM APIs', 'Payment APIs'). Use toolrate_categories to list.",
        ),
    ] = None,
    limit: Annotated[Optional[int], Field(default=None, ge=1, le=50, description="Max results (default 10).")] = None,
) -> str:
    try:
        body, rate_limit = await api_request(
            method="GET",
            path="/v1/discover/hidden-gems",
            query={"category": category, "limit": limit},
        )
    except Exception as e:
        raise_tool_error(e)

    result: dict[str, Any] = {**body}
    if rate_limit is not None:
        result["_meta"] = {"rate_limit": rate_limit}
    return json.dumps(result, indent=2)
