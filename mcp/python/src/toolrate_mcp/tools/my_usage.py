"""``toolrate_my_usage`` — check your own quota."""
from __future__ import annotations

import json
from typing import Any

from ..client import api_request
from ..errors import raise_tool_error

NAME = "toolrate_my_usage"

DESCRIPTION = (
    "Returns your tier, daily/monthly limit, calls used, and remaining quota. "
    "Use this to self-throttle before burning your free tier."
)


async def handler() -> str:
    try:
        body, rate_limit = await api_request(method="GET", path="/v1/stats/me")
    except Exception as e:
        raise_tool_error(e)

    result: dict[str, Any] = {**body}
    if rate_limit is not None:
        result["_meta"] = {"rate_limit": rate_limit}
    return json.dumps(result, indent=2)
