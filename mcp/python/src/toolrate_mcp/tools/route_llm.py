"""``toolrate_route_llm`` — fan out to 7 LLM providers, rank, return winner."""
from __future__ import annotations

import asyncio
import json
from typing import Annotated, Any, Literal, Optional

from pydantic import Field

from ..client import api_request
from ..errors import raise_tool_error

NAME = "toolrate_route_llm"

DESCRIPTION = "\n".join(
    [
        "Pick the most cost-effective LLM provider+model for a task given expected token volume, complexity, and budget caps.",
        "",
        "Considers all 7 supported providers (Anthropic, OpenAI, Groq, Together, Mistral, DeepSeek, Ollama) by default. Pass `provider` to restrict to one.",
        "",
        "Returns a flat decision object: { recommended_provider, recommended_model, cost_adjusted_score, estimated_monthly_cost, within_budget, reasoning, alternatives[] }. Use this instead of toolrate_assess when picking a model.",
        "",
        "Costs 1 ToolRate quota call per provider considered (so up to 7 by default). Use the `provider` arg to limit, or call once per workflow and reuse the result.",
    ]
)

TaskComplexity = Literal["low", "medium", "high", "very_high"]
BudgetStrategy = Literal["reliability_first", "balanced", "cost_first", "speed_first"]
ProviderKey = Literal[
    "anthropic",
    "openai",
    "groq",
    "together",
    "mistral",
    "deepseek",
    "ollama",
]

# Keep in sync with app/import_pricing.py MANUAL_PRICING canonical URLs.
PROVIDERS: list[dict[str, str]] = [
    {"key": "anthropic", "identifier": "https://api.anthropic.com/v1/messages", "display": "Anthropic"},
    {"key": "openai", "identifier": "https://api.openai.com/v1/chat/completions", "display": "OpenAI"},
    {"key": "groq", "identifier": "https://api.groq.com/openai/v1/chat/completions", "display": "Groq"},
    {"key": "together", "identifier": "https://api.together.xyz/v1/chat/completions", "display": "Together"},
    {"key": "mistral", "identifier": "https://api.mistral.ai/v1/chat/completions", "display": "Mistral"},
    {"key": "deepseek", "identifier": "https://api.deepseek.com/v1/chat/completions", "display": "DeepSeek"},
    {"key": "ollama", "identifier": "http://localhost:11434/api/chat", "display": "Ollama (local)"},
]


async def handler(
    task_description: Annotated[
        str,
        Field(min_length=1, max_length=2048, description="One-sentence description of what the LLM needs to do. Used as scoring context."),
    ],
    expected_tokens: Annotated[
        int,
        Field(gt=0, le=1_000_000, description="Total tokens (input+output) per call. Required — drives the cost math."),
    ],
    task_complexity: Annotated[
        Optional[TaskComplexity],
        Field(default=None, description="low=Haiku/mini, medium=Sonnet/4o-mini, high=Sonnet/4o, very_high=Opus/4o-large."),
    ] = None,
    max_price_per_call: Annotated[Optional[float], Field(default=None, ge=0)] = None,
    max_monthly_budget: Annotated[Optional[float], Field(default=None, ge=0)] = None,
    expected_calls_per_month: Annotated[Optional[int], Field(default=None, ge=0, le=100_000_000)] = None,
    budget_strategy: Annotated[
        Optional[BudgetStrategy],
        Field(default=None, description="Default: reliability_first. Use cost_first to minimize spend, speed_first for low latency."),
    ] = None,
    provider: Annotated[
        Optional[ProviderKey],
        Field(default=None, description="Restrict to one provider. Omit to compare all 7 and pick the best."),
    ] = None,
) -> str:
    targets = [p for p in PROVIDERS if p["key"] == provider] if provider else PROVIDERS
    if not targets:
        raise_tool_error(ValueError(f"Unknown provider '{provider}'."))

    effective_complexity = task_complexity or "medium"
    effective_strategy = budget_strategy or "reliability_first"

    async def _assess_one(p: dict[str, str]) -> tuple[dict[str, str], dict[str, Any], Any]:
        body, rate_limit = await api_request(
            method="POST",
            path="/v1/assess",
            body={
                "tool_identifier": p["identifier"],
                "context": task_description,
                "expected_tokens": expected_tokens,
                "task_complexity": effective_complexity,
                "budget_strategy": effective_strategy,
                "max_price_per_call": max_price_per_call,
                "max_monthly_budget": max_monthly_budget,
                "expected_calls_per_month": expected_calls_per_month,
            },
        )
        return p, body, rate_limit

    settled = await asyncio.gather(*[_assess_one(p) for p in targets], return_exceptions=True)

    successes: list[tuple[dict[str, str], dict[str, Any], Any]] = [
        s for s in settled if not isinstance(s, BaseException)
    ]

    if not successes:
        first = settled[0]
        raise_tool_error(first if isinstance(first, BaseException) else RuntimeError("All provider assessments failed"))

    def _rank_key(entry: tuple[dict[str, str], dict[str, Any], Any]) -> tuple[int, float]:
        _p, body, _rl = entry
        cost_score = body.get("cost_adjusted_score") or body.get("reliability_score") or 0
        over = body.get("within_budget") is False
        return (1 if over else 0, -float(cost_score))

    ranked = sorted(successes, key=_rank_key)
    winner_provider, winner_body, _winner_rate = ranked[0]
    last_rate = successes[-1][2]

    result: dict[str, Any] = {
        "recommended_provider": winner_provider["display"],
        "recommended_model": winner_body.get("recommended_model"),
        "cost_adjusted_score": winner_body.get("cost_adjusted_score"),
        "reliability_score": winner_body.get("reliability_score"),
        "estimated_monthly_cost": winner_body.get("estimated_monthly_cost"),
        "within_budget": winner_body.get("within_budget"),
        "budget_explanation": winner_body.get("budget_explanation"),
        "reasoning": winner_body.get("reasoning"),
        "alternatives": [
            {
                "provider": p["display"],
                "recommended_model": body.get("recommended_model"),
                "cost_adjusted_score": body.get("cost_adjusted_score"),
                "reliability_score": body.get("reliability_score"),
                "estimated_monthly_cost": body.get("estimated_monthly_cost"),
                "within_budget": body.get("within_budget"),
            }
            for p, body, _ in ranked[1:]
        ],
    }

    if last_rate is not None:
        result["_meta"] = {"rate_limit": last_rate, "providers_assessed": len(successes)}

    return json.dumps(result, indent=2)
