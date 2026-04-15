from __future__ import annotations

from typing import Any, Optional

import httpx

_DEFAULT_BASE_URL = "https://api.toolrate.ai"
_DEFAULT_TIMEOUT = 30.0


class ToolRate:
    """Synchronous client for the ToolRate API."""

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
        *,
        max_price_per_call: Optional[float] = None,
        max_monthly_budget: Optional[float] = None,
        expected_calls_per_month: Optional[int] = None,
        expected_tokens: Optional[int] = None,
        task_complexity: Optional[str] = None,
        budget_strategy: Optional[str] = None,
    ) -> dict[str, Any]:
        """Assess a tool's reliability and get recommendations.

        Cost-aware scoring (all optional):

        - ``max_price_per_call``: flag tools whose price exceeds this USD cap
          with ``within_budget: false`` (over-budget tools are surfaced, not
          filtered — the response always shows the best match regardless).
        - ``max_monthly_budget``: USD spend cap per month. Combines with
          ``expected_calls_per_month`` to evaluate the within_budget flag.
        - ``expected_calls_per_month``: drives ``estimated_monthly_cost`` and
          free-tier-aware effective pricing.
        - ``expected_tokens``: total tokens per LLM call (input + output).
          Triggers exact per-million-token math for providers that carry
          ``usd_per_million_input_tokens``/``usd_per_million_output_tokens``
          in their pricing. Used by the LLM router.
        - ``task_complexity``: one of ``"low"``, ``"medium"`` (default on the
          server), ``"high"``, ``"very_high"``. Picks the right model inside
          a provider (e.g. Haiku for low, Opus for very_high) and shapes the
          ``reasoning`` field.
        - ``budget_strategy``: one of ``"reliability_first"`` (default),
          ``"balanced"``, ``"cost_first"``, or ``"speed_first"``. Determines
          how ``cost_adjusted_score`` weights reliability vs. cost vs. latency.
        """
        body: dict[str, Any] = {
            "tool_identifier": tool_identifier,
            "context": context,
        }
        if sample_payload is not None:
            body["sample_payload"] = sample_payload
        if max_price_per_call is not None:
            body["max_price_per_call"] = max_price_per_call
        if max_monthly_budget is not None:
            body["max_monthly_budget"] = max_monthly_budget
        if expected_calls_per_month is not None:
            body["expected_calls_per_month"] = expected_calls_per_month
        if expected_tokens is not None:
            body["expected_tokens"] = expected_tokens
        if task_complexity is not None:
            body["task_complexity"] = task_complexity
        if budget_strategy is not None:
            body["budget_strategy"] = budget_strategy

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

    def __enter__(self) -> ToolRate:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


class AsyncToolRate:
    """Asynchronous client for the ToolRate API."""

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
        *,
        max_price_per_call: Optional[float] = None,
        max_monthly_budget: Optional[float] = None,
        expected_calls_per_month: Optional[int] = None,
        expected_tokens: Optional[int] = None,
        task_complexity: Optional[str] = None,
        budget_strategy: Optional[str] = None,
    ) -> dict[str, Any]:
        """Assess a tool's reliability and get recommendations.

        Cost-aware scoring kwargs (all optional):

        - ``max_price_per_call``: USD cap per call; tools above are flagged
          with ``within_budget: false`` rather than being filtered out.
        - ``max_monthly_budget``: monthly USD cap, combined with
          ``expected_calls_per_month``.
        - ``expected_calls_per_month``: drives ``estimated_monthly_cost`` and
          free-tier-aware effective pricing.
        - ``expected_tokens``: total tokens per LLM call (input + output).
          Triggers exact per-million-token math for providers that carry
          the per-M pricing fields. Used by the LLM router.
        - ``task_complexity``: ``"low"``, ``"medium"`` (default on the
          server), ``"high"``, ``"very_high"``. Picks the right model
          variant inside a provider.
        - ``budget_strategy``: ``"reliability_first"`` (default),
          ``"balanced"``, ``"cost_first"``, or ``"speed_first"``. The last
          strategy adds a latency dimension to the score.
        """
        body: dict[str, Any] = {
            "tool_identifier": tool_identifier,
            "context": context,
        }
        if sample_payload is not None:
            body["sample_payload"] = sample_payload
        if max_price_per_call is not None:
            body["max_price_per_call"] = max_price_per_call
        if max_monthly_budget is not None:
            body["max_monthly_budget"] = max_monthly_budget
        if expected_calls_per_month is not None:
            body["expected_calls_per_month"] = expected_calls_per_month
        if expected_tokens is not None:
            body["expected_tokens"] = expected_tokens
        if task_complexity is not None:
            body["task_complexity"] = task_complexity
        if budget_strategy is not None:
            body["budget_strategy"] = budget_strategy

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

    async def __aenter__(self) -> AsyncToolRate:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()


# Backwards-compatible aliases (deprecated names kept for existing imports)
NemoFlowClient = ToolRate
AsyncNemoFlowClient = AsyncToolRate
