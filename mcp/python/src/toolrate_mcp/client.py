"""Raw HTTP client for the ToolRate REST API.

Parallels ``mcp/typescript/src/client.ts``. We deliberately bypass the published
``toolrate`` Python SDK so responses stay snake_case and include jurisdiction
fields the SDK strips during its type mapping.
"""
from __future__ import annotations

import os
from typing import Any, Mapping

import httpx

from . import __version__

DEFAULT_BASE_URL = "https://api.toolrate.ai"
DEFAULT_TIMEOUT_S = 30.0


class RateLimitInfo(dict):
    """Typed dict helper. Values may be ints or None."""


class ApiError(Exception):
    """Error returned by the ToolRate REST API (or the transport layer)."""

    def __init__(
        self,
        message: str,
        status: int,
        body: Any = None,
        rate_limit: RateLimitInfo | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.body = body
        self.rate_limit = rate_limit


def get_api_key() -> str | None:
    raw = os.environ.get("TOOLRATE_API_KEY", "").strip()
    return raw or None


def get_base_url() -> str:
    raw = os.environ.get("TOOLRATE_BASE_URL", "").strip() or DEFAULT_BASE_URL
    return raw.rstrip("/")


def _strip_none(d: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _read_rate_limit(headers: httpx.Headers) -> RateLimitInfo | None:
    limit = headers.get("x-ratelimit-limit")
    remaining = headers.get("x-ratelimit-remaining")
    reset = headers.get("x-ratelimit-reset")
    if not limit and not remaining and not reset:
        return None
    return RateLimitInfo(
        limit=int(limit) if limit else None,
        remaining=int(remaining) if remaining else None,
        reset_at=reset if reset else None,
    )


async def api_request(
    method: str,
    path: str,
    body: Mapping[str, Any] | None = None,
    query: Mapping[str, Any] | None = None,
    authenticated: bool = True,
) -> tuple[Any, RateLimitInfo | None]:
    """Call the ToolRate API. Returns ``(parsed_body, rate_limit)``.

    Raises :class:`ApiError` on any non-2xx, timeout, or transport failure.
    """
    base_url = get_base_url()
    url = f"{base_url}{path}"

    headers: dict[str, str] = {
        "Accept": "application/json",
        "User-Agent": f"toolrate-mcp-python/{__version__}",
    }

    if authenticated:
        api_key = get_api_key()
        if not api_key:
            raise ApiError(
                "TOOLRATE_API_KEY env var is not set. Add it to your MCP "
                "server config or call toolrate_register to get a free key.",
                status=401,
            )
        headers["X-Api-Key"] = api_key

    params: dict[str, Any] | None = None
    if query:
        params = {k: v for k, v in query.items() if v not in (None, "")}

    json_body: dict[str, Any] | None = None
    if body is not None:
        json_body = _strip_none(body)

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_S) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_body,
            )
    except httpx.TimeoutException:
        raise ApiError(
            f"ToolRate request timed out after {int(DEFAULT_TIMEOUT_S * 1000)}ms",
            status=0,
        )
    except httpx.HTTPError as e:
        raise ApiError(f"ToolRate network error: {e}", status=0)

    rate_limit = _read_rate_limit(response.headers)

    parsed: Any = None
    parse_failed = False
    if response.text:
        try:
            parsed = response.json()
        except ValueError:
            parse_failed = True

    if response.status_code >= 400:
        raise ApiError(
            f"ToolRate API error: {response.status_code} {response.reason_phrase}",
            status=response.status_code,
            body=parsed,
            rate_limit=rate_limit,
        )

    if parse_failed or parsed is None:
        raise ApiError(
            f"ToolRate API returned an empty or malformed response body "
            f"(HTTP {response.status_code})",
            status=response.status_code,
            rate_limit=rate_limit,
        )

    return parsed, rate_limit
