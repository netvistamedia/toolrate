"""Intelligent Cost-Aware LLM Router — example using the ToolRate API.

Drop this file into your agent project for automatic model selection
across LLM providers (Claude, GPT, Llama-on-Groq, Llama-on-Together,
Mistral, DeepSeek). Every call is assessed by ToolRate for reliability,
cost, latency, and model fit, and the best-scoring provider is picked.

Quick start
-----------

    import asyncio
    from toolrate import AsyncToolRate
    from llm_router import LLMRouter

    class MyRouter(LLMRouter):
        async def _dispatch(self, decision, prompt):
            # Wire up your preferred HTTP client / provider SDK here.
            # decision.provider is the ToolRate identifier (e.g. the
            # full /v1/chat/completions URL); decision.model is the
            # specific model the router picked inside that provider.
            ...

    async def main():
        async with AsyncToolRate(api_key="nf_live_...") as tr:
            router = MyRouter(
                tr,
                max_price_per_call=0.01,
                expected_calls_per_month=50_000,
            )
            result = await router.route(
                prompt="Summarize this meeting transcript in 3 bullets.",
                task_complexity="medium",
                expected_tokens=1500,
                budget_strategy="balanced",
            )
            print(result["response"])
            print(result["routing"])

    asyncio.run(main())

Design notes
------------

The router makes two separate decisions:

1. **Provider selection** — which of the configured providers to hit.
   ToolRate's /v1/assess returns a cost_adjusted_score per provider,
   weighted by the caller's budget_strategy. The highest in-budget
   score wins; if nothing fits the budget, the highest over-budget
   score is chosen with within_budget=False flagged on the decision.

2. **Model selection within a provider** — which model inside the
   winning provider to use. ToolRate returns ``recommended_model``
   populated from the provider's model catalog (Anthropic → Haiku/
   Sonnet/Opus, OpenAI → gpt-4o-mini/gpt-4o/o3-mini, etc.) based on
   the caller's task_complexity + budget_strategy. The router hands
   that string to ``_dispatch`` so provider-specific code can call
   the exact model.

Subclass ``_dispatch`` to wire up the actual HTTP/SDK calls. The base
class does the decision-making only — it doesn't pin you to any
particular LLM SDK.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from toolrate import AsyncToolRate

logger = logging.getLogger("toolrate.llm_router")


# Every LLM provider ToolRate's default catalog (as of 2026-04-15) covers
# with a full models[] array. These are the identifiers you'd see in the
# ToolRate /v1/assess response. Override via ``providers=`` at construction
# time to narrow or extend the pool.
DEFAULT_PROVIDERS: tuple[str, ...] = (
    "https://api.anthropic.com/v1/messages",
    "https://api.openai.com/v1/chat/completions",
    "https://api.groq.com/openai/v1/chat/completions",
    "https://api.together.xyz/v1/chat/completions",
    "https://api.mistral.ai/v1/chat/completions",
    "https://api.deepseek.com/v1/chat/completions",
)


@dataclass(frozen=True)
class RoutingDecision:
    """Everything the router chose and why. Logged, returned, and replayable.

    ``reasoning`` is the human-readable explanation produced by ToolRate
    itself — drop it straight into your logs or a debug UI. The rest of
    the fields are there for programmatic use (metrics, audit trails,
    A/B comparisons).
    """

    provider: str
    model: Optional[str]
    reliability_score: float
    cost_adjusted_score: float
    price_per_call: Optional[float]
    estimated_monthly_cost: Optional[float]
    within_budget: bool
    reasoning: str
    strategy: str
    task_complexity: str
    # Every provider we evaluated, keyed by identifier → score. Useful for
    # "why didn't you pick X?" debugging and for training eval harnesses.
    considered: dict[str, float] = field(default_factory=dict)

    def __str__(self) -> str:
        model_part = f" ({self.model})" if self.model else ""
        budget_part = "" if self.within_budget else " [OVER BUDGET]"
        return (
            f"LLMRouter → {self.provider}{model_part}  "
            f"score={self.cost_adjusted_score:.1f}  "
            f"strategy={self.strategy}{budget_part}"
        )


class LLMRouter:
    """Drop-in router that picks the right LLM for each call.

    Parameters
    ----------
    toolrate
        A connected ``AsyncToolRate`` client. The router doesn't own the
        lifecycle — close it yourself (or use ``async with``).
    providers
        Iterable of ToolRate tool identifiers. Defaults to the six
        LLM providers in ``DEFAULT_PROVIDERS``. Narrow this to e.g.
        ``("https://api.anthropic.com/v1/messages",)`` if you only
        want to router between Claude models.
    max_price_per_call, max_monthly_budget, expected_calls_per_month
        Budget caps applied to every assessment. Override per call if
        needed via ``choose`` / ``route``.
    context
        Optional ToolRate context string (e.g. workflow name) passed
        with each assessment. Improves context-bucketed scoring.
    """

    def __init__(
        self,
        toolrate: AsyncToolRate,
        *,
        providers: tuple[str, ...] | list[str] = DEFAULT_PROVIDERS,
        max_price_per_call: Optional[float] = None,
        max_monthly_budget: Optional[float] = None,
        expected_calls_per_month: Optional[int] = None,
        context: str = "",
    ) -> None:
        self._tr = toolrate
        self._providers: tuple[str, ...] = tuple(providers)
        if not self._providers:
            raise ValueError("LLMRouter needs at least one provider")
        self._max_price_per_call = max_price_per_call
        self._max_monthly_budget = max_monthly_budget
        self._expected_calls_per_month = expected_calls_per_month
        self._context = context

    # -- Decision ------------------------------------------------------------

    async def choose(
        self,
        *,
        task_complexity: str = "medium",
        expected_tokens: int = 1000,
        budget_strategy: str = "balanced",
    ) -> RoutingDecision:
        """Ask ToolRate to score every provider and pick the winner.

        Pure decision step — no LLM calls are made. Useful when you want
        to log routing decisions without dispatching, or when you already
        have the prompt pipeline wired up and just need the "who".
        """
        results = await self._assess_all(
            task_complexity=task_complexity,
            expected_tokens=expected_tokens,
            budget_strategy=budget_strategy,
        )
        return self._pick_winner(
            results,
            task_complexity=task_complexity,
            budget_strategy=budget_strategy,
        )

    async def route(
        self,
        prompt: str,
        *,
        task_complexity: str = "medium",
        expected_tokens: int = 1000,
        budget_strategy: str = "balanced",
        max_fallbacks: int = 2,
    ) -> dict[str, Any]:
        """Pick an LLM and call it with the given prompt.

        Returns ``{"response", "provider", "model", "routing": RoutingDecision,
        "fallbacks": [...]}``. On dispatch failure, the router falls back
        to the next-best provider up to ``max_fallbacks`` times. Each
        fallback is recorded on the ``fallbacks`` list with the exception
        that triggered it — handy for post-mortems.
        """
        results = await self._assess_all(
            task_complexity=task_complexity,
            expected_tokens=expected_tokens,
            budget_strategy=budget_strategy,
        )
        # Sort providers by cost_adjusted_score, preferring in-budget picks.
        # This gives us a natural fallback cascade: if the top pick fails,
        # try the next best, then the next.
        ranked = self._ranked_candidates(results)
        if not ranked:
            raise RuntimeError(
                "LLMRouter: no provider returned a usable assessment"
            )

        fallbacks: list[dict[str, Any]] = []
        last_error: Optional[Exception] = None

        for attempt_index, (provider, payload) in enumerate(ranked[: max_fallbacks + 1]):
            decision = self._decision_from_payload(
                provider, payload, results,
                task_complexity=task_complexity,
                budget_strategy=budget_strategy,
            )
            try:
                response = await self._dispatch(decision, prompt)
            except Exception as exc:  # noqa: BLE001 - fallback cascade is the point
                logger.warning(
                    "LLMRouter: dispatch failed for %s (%s) — falling back",
                    provider, exc,
                )
                fallbacks.append({
                    "provider": provider,
                    "model": decision.model,
                    "error": repr(exc),
                })
                last_error = exc
                # Report the failure back to ToolRate so the score reflects
                # the real-world failure next time. Best-effort — a reporting
                # failure must not mask the original error.
                try:
                    await self._tr.report(
                        tool_identifier=provider,
                        success=False,
                        error_category="server_error",
                    )
                except Exception:  # noqa: BLE001
                    logger.debug("LLMRouter: failed to report failure to ToolRate")
                continue

            # Success! Report it too, so the scoring loop stays honest.
            try:
                await self._tr.report(
                    tool_identifier=provider,
                    success=True,
                )
            except Exception:  # noqa: BLE001
                logger.debug("LLMRouter: failed to report success to ToolRate")

            return {
                "response": response,
                "provider": decision.provider,
                "model": decision.model,
                "routing": decision,
                "fallbacks": fallbacks,
            }

        raise RuntimeError(
            f"LLMRouter: all {len(ranked[: max_fallbacks + 1])} candidates "
            f"failed; last error = {last_error!r}"
        )

    # -- Dispatch hook -------------------------------------------------------

    async def _dispatch(self, decision: RoutingDecision, prompt: str) -> Any:
        """Override this to call the actual LLM provider.

        The base implementation raises ``NotImplementedError`` — subclass
        ``LLMRouter`` and fill in your own HTTP client (or provider SDK)
        logic here. ``decision.provider`` is the ToolRate tool identifier
        (i.e. the full API URL); ``decision.model`` is the specific model
        to call inside that provider.

        Typical implementations delegate to the provider's native SDK:

            if decision.provider.startswith("https://api.anthropic.com"):
                client = anthropic.AsyncClient()
                msg = await client.messages.create(
                    model=decision.model or "claude-sonnet-4-6",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024,
                )
                return msg.content[0].text
            elif decision.provider.startswith("https://api.openai.com"):
                client = openai.AsyncOpenAI()
                resp = await client.chat.completions.create(
                    model=decision.model or "gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                )
                return resp.choices[0].message.content
            ...
        """
        raise NotImplementedError(
            "Subclass LLMRouter and implement _dispatch() for your providers. "
            f"Got a decision to call {decision.provider} "
            f"(model={decision.model!r}) but no dispatch wired up."
        )

    # -- Internal helpers ----------------------------------------------------

    async def _assess_all(
        self,
        *,
        task_complexity: str,
        expected_tokens: int,
        budget_strategy: str,
    ) -> dict[str, dict[str, Any]]:
        """Assess every configured provider in parallel. Failures become None."""

        async def _assess_one(provider: str) -> tuple[str, Optional[dict[str, Any]]]:
            try:
                payload = await self._tr.assess(
                    tool_identifier=provider,
                    context=self._context,
                    max_price_per_call=self._max_price_per_call,
                    max_monthly_budget=self._max_monthly_budget,
                    expected_calls_per_month=self._expected_calls_per_month,
                    expected_tokens=expected_tokens,
                    task_complexity=task_complexity,
                    budget_strategy=budget_strategy,
                )
                return provider, payload
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "LLMRouter: assess failed for %s (%s)", provider, exc
                )
                return provider, None

        pairs = await asyncio.gather(
            *(_assess_one(p) for p in self._providers)
        )
        return {provider: payload for provider, payload in pairs if payload is not None}

    def _ranked_candidates(
        self, results: dict[str, dict[str, Any]]
    ) -> list[tuple[str, dict[str, Any]]]:
        """Sort candidates by (in-budget first, then cost_adjusted_score desc)."""
        def _sort_key(item: tuple[str, dict[str, Any]]) -> tuple[int, float]:
            _, payload = item
            # within_budget is False/True/None — treat None as "unknown,
            # assume fits" so new providers without pricing data aren't
            # unconditionally demoted.
            in_budget = payload.get("within_budget") is not False
            score = payload.get("cost_adjusted_score")
            if score is None:
                score = payload.get("reliability_score", 0.0)
            return (0 if in_budget else 1, -float(score))

        return sorted(results.items(), key=_sort_key)

    def _pick_winner(
        self,
        results: dict[str, dict[str, Any]],
        *,
        task_complexity: str,
        budget_strategy: str,
    ) -> RoutingDecision:
        ranked = self._ranked_candidates(results)
        if not ranked:
            raise RuntimeError(
                "LLMRouter: no provider returned a usable assessment"
            )
        winner, payload = ranked[0]
        return self._decision_from_payload(
            winner, payload, results,
            task_complexity=task_complexity,
            budget_strategy=budget_strategy,
        )

    def _decision_from_payload(
        self,
        provider: str,
        payload: dict[str, Any],
        all_results: dict[str, dict[str, Any]],
        *,
        task_complexity: str,
        budget_strategy: str,
    ) -> RoutingDecision:
        considered = {
            p: float(r.get("cost_adjusted_score") or r.get("reliability_score") or 0.0)
            for p, r in all_results.items()
        }
        return RoutingDecision(
            provider=provider,
            model=payload.get("recommended_model"),
            reliability_score=float(payload.get("reliability_score") or 0.0),
            cost_adjusted_score=float(
                payload.get("cost_adjusted_score")
                or payload.get("reliability_score")
                or 0.0
            ),
            price_per_call=payload.get("price_per_call"),
            estimated_monthly_cost=payload.get("estimated_monthly_cost"),
            within_budget=payload.get("within_budget") is not False,
            reasoning=payload.get("reasoning") or "",
            strategy=budget_strategy,
            task_complexity=task_complexity,
            considered=considered,
        )


# ---------------------------------------------------------------------------
# Usage example
# ---------------------------------------------------------------------------
#
# Save this alongside llm_router.py and run it as ``python example_usage.py``.
# The class below wires up a single provider (Anthropic) for demonstration
# purposes — in production you'd wire up all six providers you care about,
# each with its native SDK.
#
# ```python
# import asyncio
# from toolrate import AsyncToolRate
# from llm_router import LLMRouter, RoutingDecision
#
# # anthropic is an optional dep — install separately with `uv add anthropic`
# import anthropic
#
#
# class ProductionRouter(LLMRouter):
#     def __init__(self, tr, anthropic_client, **kwargs):
#         super().__init__(tr, **kwargs)
#         self._anthropic = anthropic_client
#
#     async def _dispatch(self, decision: RoutingDecision, prompt: str) -> str:
#         if decision.provider.startswith("https://api.anthropic.com"):
#             msg = await self._anthropic.messages.create(
#                 model=decision.model or "claude-sonnet-4-6",
#                 max_tokens=2048,
#                 messages=[{"role": "user", "content": prompt}],
#             )
#             return msg.content[0].text
#         raise NotImplementedError(
#             f"No dispatcher wired for {decision.provider}"
#         )
#
#
# async def main():
#     async with AsyncToolRate(api_key="nf_live_...") as tr:
#         router = ProductionRouter(
#             tr,
#             anthropic_client=anthropic.AsyncAnthropic(),
#             providers=("https://api.anthropic.com/v1/messages",),
#             max_price_per_call=0.01,
#             expected_calls_per_month=50_000,
#         )
#
#         # 1. Simple summarization — low complexity → likely Haiku
#         result = await router.route(
#             prompt="Summarize: the sky is blue and the grass is green.",
#             task_complexity="low",
#             expected_tokens=200,
#             budget_strategy="cost_first",
#         )
#         print(result["routing"])           # → ... (claude-haiku-4-5) ...
#
#         # 2. Deep reasoning — very_high → Opus
#         result = await router.route(
#             prompt="Prove the Riemann hypothesis in 3 paragraphs.",
#             task_complexity="very_high",
#             expected_tokens=4000,
#             budget_strategy="reliability_first",
#         )
#         print(result["routing"])           # → ... (claude-opus-4-6) ...
#
#         # 3. High-volume production: speed matters more than quality
#         result = await router.route(
#             prompt="Classify this email: [...]",
#             task_complexity="low",
#             expected_tokens=400,
#             budget_strategy="speed_first",
#         )
#         print(result["routing"])           # → ... fastest capable model ...
#
#
# asyncio.run(main())
# ```
