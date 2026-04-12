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

    # -- Assessment ------------------------------------------------------------

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

    def assess_batch(
        self,
        tools: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Assess up to 20 tools in a single request.

        Args:
            tools: List of dicts with 'tool_identifier' and optional 'context'.
                   Example: [{"tool_identifier": "https://api.stripe.com/v1/charges", "context": "payment"}]
        """
        resp = self._client.post("/v1/assess/batch", json={"tools": tools})
        resp.raise_for_status()
        return resp.json()

    # -- Reporting -------------------------------------------------------------

    def report(
        self,
        tool_identifier: str,
        success: bool,
        error_category: Optional[str] = None,
        latency_ms: Optional[int] = None,
        context: str = "",
        session_id: Optional[str] = None,
        attempt_number: Optional[int] = None,
        previous_tool: Optional[str] = None,
    ) -> dict[str, Any]:
        """Report a tool execution outcome.

        For journey tracking, include session_id, attempt_number, and
        previous_tool when retrying after a failure. This data powers
        the hidden gems and fallback chain features.
        """
        body: dict[str, Any] = {
            "tool_identifier": tool_identifier,
            "success": success,
            "context": context,
        }
        if error_category is not None:
            body["error_category"] = error_category
        if latency_ms is not None:
            body["latency_ms"] = latency_ms
        if session_id is not None:
            body["session_id"] = session_id
        if attempt_number is not None:
            body["attempt_number"] = attempt_number
        if previous_tool is not None:
            body["previous_tool"] = previous_tool

        resp = self._client.post("/v1/report", json=body)
        resp.raise_for_status()
        return resp.json()

    # -- Discovery -------------------------------------------------------------

    def discover_hidden_gems(
        self, category: Optional[str] = None, limit: int = 10
    ) -> dict[str, Any]:
        """Find hidden gem tools that shine as fallbacks."""
        params: dict[str, Any] = {"limit": limit}
        if category:
            params["category"] = category
        resp = self._client.get("/v1/discover/hidden-gems", params=params)
        resp.raise_for_status()
        return resp.json()

    def discover_fallback_chain(
        self, tool_identifier: str, limit: int = 5
    ) -> dict[str, Any]:
        """Get the best fallback tools when this tool fails."""
        resp = self._client.get(
            "/v1/discover/fallback-chain",
            params={"tool_identifier": tool_identifier, "limit": limit},
        )
        resp.raise_for_status()
        return resp.json()

    # -- Tools -----------------------------------------------------------------

    def search_tools(
        self,
        q: Optional[str] = None,
        category: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search and browse all rated tools."""
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if q:
            params["q"] = q
        if category:
            params["category"] = category
        resp = self._client.get("/v1/tools", params=params)
        resp.raise_for_status()
        return resp.json()

    def list_categories(self) -> dict[str, Any]:
        """List all tool categories with counts."""
        resp = self._client.get("/v1/tools/categories")
        resp.raise_for_status()
        return resp.json()

    # -- Stats -----------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get platform-wide statistics."""
        resp = self._client.get("/v1/stats")
        resp.raise_for_status()
        return resp.json()

    def get_my_stats(self) -> dict[str, Any]:
        """Get personal usage statistics (tier, limits, usage)."""
        resp = self._client.get("/v1/stats/me")
        resp.raise_for_status()
        return resp.json()

    # -- Webhooks --------------------------------------------------------------

    def create_webhook(
        self,
        url: str,
        threshold: int = 5,
        tool_identifier: Optional[str] = None,
        event: str = "score.change",
    ) -> dict[str, Any]:
        """Register a webhook for score change alerts.

        Returns the webhook details including the HMAC signing secret
        (only shown once — store it securely).
        """
        body: dict[str, Any] = {"url": url, "event": event, "threshold": threshold}
        if tool_identifier is not None:
            body["tool_identifier"] = tool_identifier
        resp = self._client.post("/v1/webhooks", json=body)
        resp.raise_for_status()
        return resp.json()

    def list_webhooks(self) -> dict[str, Any]:
        """List all your registered webhooks."""
        resp = self._client.get("/v1/webhooks")
        resp.raise_for_status()
        return resp.json()

    def delete_webhook(self, webhook_id: str) -> dict[str, Any]:
        """Delete a webhook by ID."""
        resp = self._client.delete(f"/v1/webhooks/{webhook_id}")
        resp.raise_for_status()
        return resp.json()

    # -- Account ---------------------------------------------------------------

    def rotate_key(self) -> dict[str, Any]:
        """Rotate your API key. Returns a new key; the current key is deactivated.

        Important: Update your client with the new key after calling this.
        """
        resp = self._client.post("/v1/auth/rotate-key")
        resp.raise_for_status()
        return resp.json()

    def delete_account(self) -> dict[str, Any]:
        """Permanently delete your account and all associated data.

        This action cannot be undone. Your API key will be deactivated
        and all webhooks removed.
        """
        resp = self._client.delete("/v1/account")
        resp.raise_for_status()
        return resp.json()

    # -- Lifecycle -------------------------------------------------------------

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

    # -- Assessment ------------------------------------------------------------

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

    async def assess_batch(
        self,
        tools: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Assess up to 20 tools in a single request."""
        resp = await self._client.post("/v1/assess/batch", json={"tools": tools})
        resp.raise_for_status()
        return resp.json()

    # -- Reporting -------------------------------------------------------------

    async def report(
        self,
        tool_identifier: str,
        success: bool,
        error_category: Optional[str] = None,
        latency_ms: Optional[int] = None,
        context: str = "",
        session_id: Optional[str] = None,
        attempt_number: Optional[int] = None,
        previous_tool: Optional[str] = None,
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
        if session_id is not None:
            body["session_id"] = session_id
        if attempt_number is not None:
            body["attempt_number"] = attempt_number
        if previous_tool is not None:
            body["previous_tool"] = previous_tool

        resp = await self._client.post("/v1/report", json=body)
        resp.raise_for_status()
        return resp.json()

    # -- Discovery -------------------------------------------------------------

    async def discover_hidden_gems(
        self, category: Optional[str] = None, limit: int = 10
    ) -> dict[str, Any]:
        """Find hidden gem tools that shine as fallbacks."""
        params: dict[str, Any] = {"limit": limit}
        if category:
            params["category"] = category
        resp = await self._client.get("/v1/discover/hidden-gems", params=params)
        resp.raise_for_status()
        return resp.json()

    async def discover_fallback_chain(
        self, tool_identifier: str, limit: int = 5
    ) -> dict[str, Any]:
        """Get the best fallback tools when this tool fails."""
        resp = await self._client.get(
            "/v1/discover/fallback-chain",
            params={"tool_identifier": tool_identifier, "limit": limit},
        )
        resp.raise_for_status()
        return resp.json()

    # -- Tools -----------------------------------------------------------------

    async def search_tools(
        self,
        q: Optional[str] = None,
        category: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search and browse all rated tools."""
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if q:
            params["q"] = q
        if category:
            params["category"] = category
        resp = await self._client.get("/v1/tools", params=params)
        resp.raise_for_status()
        return resp.json()

    async def list_categories(self) -> dict[str, Any]:
        """List all tool categories with counts."""
        resp = await self._client.get("/v1/tools/categories")
        resp.raise_for_status()
        return resp.json()

    # -- Stats -----------------------------------------------------------------

    async def get_stats(self) -> dict[str, Any]:
        """Get platform-wide statistics."""
        resp = await self._client.get("/v1/stats")
        resp.raise_for_status()
        return resp.json()

    async def get_my_stats(self) -> dict[str, Any]:
        """Get personal usage statistics (tier, limits, usage)."""
        resp = await self._client.get("/v1/stats/me")
        resp.raise_for_status()
        return resp.json()

    # -- Webhooks --------------------------------------------------------------

    async def create_webhook(
        self,
        url: str,
        threshold: int = 5,
        tool_identifier: Optional[str] = None,
        event: str = "score.change",
    ) -> dict[str, Any]:
        """Register a webhook for score change alerts."""
        body: dict[str, Any] = {"url": url, "event": event, "threshold": threshold}
        if tool_identifier is not None:
            body["tool_identifier"] = tool_identifier
        resp = await self._client.post("/v1/webhooks", json=body)
        resp.raise_for_status()
        return resp.json()

    async def list_webhooks(self) -> dict[str, Any]:
        """List all your registered webhooks."""
        resp = await self._client.get("/v1/webhooks")
        resp.raise_for_status()
        return resp.json()

    async def delete_webhook(self, webhook_id: str) -> dict[str, Any]:
        """Delete a webhook by ID."""
        resp = await self._client.delete(f"/v1/webhooks/{webhook_id}")
        resp.raise_for_status()
        return resp.json()

    # -- Account ---------------------------------------------------------------

    async def rotate_key(self) -> dict[str, Any]:
        """Rotate your API key. Returns a new key; the current key is deactivated."""
        resp = await self._client.post("/v1/auth/rotate-key")
        resp.raise_for_status()
        return resp.json()

    async def delete_account(self) -> dict[str, Any]:
        """Permanently delete your account and all associated data."""
        resp = await self._client.delete("/v1/account")
        resp.raise_for_status()
        return resp.json()

    # -- Lifecycle -------------------------------------------------------------

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncNemoFlowClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
