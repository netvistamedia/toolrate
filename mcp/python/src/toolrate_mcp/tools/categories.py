"""``toolrate_categories`` — list canonical categories with counts."""
from __future__ import annotations

import json
from typing import Any

from ..client import api_request
from ..errors import raise_tool_error

NAME = "toolrate_categories"

DESCRIPTION = "Get the canonical category names + tool counts. Useful to filter toolrate_search_tools or toolrate_hidden_gems."


async def handler() -> str:
    try:
        body, rate_limit = await api_request(method="GET", path="/v1/tools/categories")
    except Exception as e:
        raise_tool_error(e)

    result: dict[str, Any] = {**body}
    if rate_limit is not None:
        result["_meta"] = {"rate_limit": rate_limit}
    return json.dumps(result, indent=2)
