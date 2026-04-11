from __future__ import annotations

from typing import Any, Optional

import httpx

_DEFAULT_BASE_URL = "https://api.nemoflow.ai"
_DEFAULT_TIMEOUT = 30.0


class NemoFlowClient:
    """Synchronous client for the NemoFlow API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"X-Api-Key": self._api_key},
            timeout=timeout,
        )

    # -- endpoints -----------------------------------------------------------

    def assess(
        self,
        tool_identifier: str,
        context: str = "",
        sample_payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Assess a tool's reliability and get recommendations."""
        body: dict[str, Any] = {
            "tool_identifier": tool_identifier,
            "context": context,
        }
        if sample_payload is not None:
            body["sample_payload"] = sample_payload

        resp = self._client.post("/v1/assess", json=body)
        resp.raise_for_status()
        return resp.json()

    def report(
        self,
        tool_identifier: str,
        success: bool,
        error_category: Optional[str] = None,
        latency_ms: Optional[int] = None,
        context: str = "",
    ) -> dict[str, Any]:
        """Report a tool execution outcome."""
        body: dict[str, Any] = {
            "tool_identifier": tool_identifier,
            "success": success,
            "context": context,
        }
        if error_category is not None:
            body["error_category"] = error_category
        if latency_ms is not None:
            body["latency_ms"] = latency_ms

        resp = self._client.post("/v1/report", json=body)
        resp.raise_for_status()
        return resp.json()

    # -- lifecycle -----------------------------------------------------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> NemoFlowClient:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


class AsyncNemoFlowClient:
    """Asynchronous client for the NemoFlow API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"X-Api-Key": self._api_key},
            timeout=timeout,
        )

    # -- endpoints -----------------------------------------------------------

    async def assess(
        self,
        tool_identifier: str,
        context: str = "",
        sample_payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Assess a tool's reliability and get recommendations."""
        body: dict[str, Any] = {
            "tool_identifier": tool_identifier,
            "context": context,
        }
        if sample_payload is not None:
            body["sample_payload"] = sample_payload

        resp = await self._client.post("/v1/assess", json=body)
        resp.raise_for_status()
        return resp.json()

    async def report(
        self,
        tool_identifier: str,
        success: bool,
        error_category: Optional[str] = None,
        latency_ms: Optional[int] = None,
        context: str = "",
    ) -> dict[str, Any]:
        """Report a tool execution outcome."""
        body: dict[str, Any] = {
            "tool_identifier": tool_identifier,
            "success": success,
            "context": context,
        }
        if error_category is not None:
            body["error_category"] = error_category
        if latency_ms is not None:
            body["latency_ms"] = latency_ms

        resp = await self._client.post("/v1/report", json=body)
        resp.raise_for_status()
        return resp.json()

    # -- lifecycle -----------------------------------------------------------

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncNemoFlowClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
