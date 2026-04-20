"""Map :class:`ApiError` to human-readable strings for tool return values.

Parallels ``mcp/typescript/src/errors.ts``. FastMCP expects handlers to return
strings (or structured content); raising from a handler translates to an
``isError: true`` tool result. We surface the formatted string by raising
``ToolError`` in each handler wrapper.
"""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp.exceptions import ToolError

from .client import ApiError


def raise_tool_error(err: BaseException) -> None:
    """Raise a ``ToolError`` with the human-readable explanation.

    Handlers should call this from an ``except Exception as e`` branch so
    FastMCP reports ``isError: true`` with a useful message the agent can read.
    """
    raise ToolError(_format_error(err)) from err


def _format_error(err: BaseException) -> str:
    if isinstance(err, ApiError):
        return _format_api_error(err)
    if isinstance(err, Exception):
        return f"ToolRate MCP error: {err}"
    return f"ToolRate MCP error: {err!r}"


def _format_api_error(err: ApiError) -> str:
    detail = _extract_detail(err.body)

    if err.status == 0:
        return (
            f"Cannot reach the ToolRate API. {err} — check your internet or "
            "TOOLRATE_BASE_URL."
        )
    if err.status == 401:
        return (
            "ToolRate API rejected the API key (401). Check TOOLRATE_API_KEY "
            "in your MCP config."
        )
    if err.status == 403:
        return (
            f"ToolRate API forbade this request (403). "
            f"{detail or 'Your tier likely cannot access this endpoint.'}"
        )
    if err.status == 404:
        return (
            f"ToolRate API: not found (404). "
            f"{detail or 'If this was an unrated tool, the assess endpoint usually triggers an LLM-estimated cold start instead.'}"
        )
    if err.status == 422:
        return (
            "ToolRate API validation error (422): "
            f"{detail or 'check the parameters you passed.'}"
        )
    if err.status == 429:
        rl = err.rate_limit or {}
        remaining = rl.get("remaining") if isinstance(rl, dict) else None
        limit = rl.get("limit") if isinstance(rl, dict) else None
        ctx = f" ({remaining}/{limit} remaining)" if remaining is not None and limit is not None else ""
        return (
            f"ToolRate API rate limit exceeded (429){ctx}. Free tier is 100 "
            "assessments/day. Run toolrate_my_usage to check your quota."
        )
    if err.status in (500, 502, 503, 504):
        return (
            f"ToolRate API is having issues ({err.status}). "
            f"{detail or 'Please retry in a moment.'}"
        )
    return f"ToolRate API error ({err.status}): {detail or err}"


def _extract_detail(body: Any) -> str | None:
    if not isinstance(body, dict):
        return None
    if isinstance(body.get("detail"), str):
        return body["detail"]
    if isinstance(body.get("message"), str):
        return body["message"]
    errors = body.get("errors")
    if isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, dict) and isinstance(first.get("msg"), str):
            return first["msg"]
    return None
