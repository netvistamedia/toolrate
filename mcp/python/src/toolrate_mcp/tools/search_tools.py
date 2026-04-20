"""``toolrate_search_tools`` — browse the ToolRate catalog."""
from __future__ import annotations

import json
from typing import Annotated, Any, Optional

from pydantic import Field

from ..client import api_request
from ..errors import raise_tool_error

NAME = "toolrate_search_tools"

DESCRIPTION = "\n".join(
    [
        "Search the ToolRate catalog by name, identifier substring, or category. Returns identifiers you can pass to toolrate_assess.",
        "",
        "Use this when the agent needs to find candidate tools for a task but doesn't know the canonical identifier.",
    ]
)


async def handler(
    q: Annotated[
        Optional[str],
        Field(default=None, max_length=256, description="Search by tool name or identifier (case-insensitive substring)."),
    ] = None,
    category: Annotated[Optional[str], Field(default=None, max_length=128, description="Filter by category.")] = None,
    limit: Annotated[Optional[int], Field(default=None, ge=1, le=200, description="Max results (default 50).")] = None,
    offset: Annotated[Optional[int], Field(default=None, ge=0, le=10_000, description="Pagination offset.")] = None,
) -> str:
    try:
        body, rate_limit = await api_request(
            method="GET",
            path="/v1/tools",
            query={"q": q, "category": category, "limit": limit, "offset": offset},
        )
    except Exception as e:
        raise_tool_error(e)

    result: dict[str, Any] = {**body}
    if rate_limit is not None:
        result["_meta"] = {"rate_limit": rate_limit}
    return json.dumps(result, indent=2)
