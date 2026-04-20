"""``toolrate_assess`` — crown-jewel reliability scoring tool."""
from __future__ import annotations

import json
from typing import Annotated, Any, Literal, Optional

from pydantic import Field

from ..client import api_request
from ..errors import raise_tool_error
from ..summary import make_summary

NAME = "toolrate_assess"

DESCRIPTION = "\n".join(
    [
        "Get ToolRate's reliability score (0-100), pitfalls, mitigations, and the best alternatives for any third-party tool/API the agent is about to call.",
        "",
        "Guard pattern: call this BEFORE invoking the actual third-party tool. After the real call returns, call toolrate_report.",
        "",
        "For LLM provider selection, prefer toolrate_route_llm — it's a simpler interface that returns just the routing fields.",
        "",
        "Quota tip: assess once per tool per workflow, not per call. The API caches 5min server-side. Use toolrate_my_usage to check remaining quota.",
    ]
)

TaskComplexity = Literal["low", "medium", "high", "very_high"]
BudgetStrategy = Literal["reliability_first", "balanced", "cost_first", "speed_first"]


async def handler(
    tool_identifier: Annotated[
        str,
        Field(
            min_length=1,
            max_length=512,
            description=(
                "URL or canonical name of the tool to assess. Examples: "
                "'https://api.stripe.com/v1/charges', 'sendgrid'."
            ),
        ),
    ],
    context: Annotated[
        Optional[str],
        Field(
            default=None,
            max_length=1024,
            description="Workflow context for context-bucketed scoring, e.g. 'high-value payment processing'.",
        ),
    ] = None,
    max_price_per_call: Annotated[
        Optional[float],
        Field(default=None, ge=0, description="USD cap per call. Tools above are flagged within_budget=false (not filtered)."),
    ] = None,
    max_monthly_budget: Annotated[
        Optional[float],
        Field(default=None, ge=0, description="Max USD spend per month. Combines with expected_calls_per_month for the budget check."),
    ] = None,
    expected_calls_per_month: Annotated[
        Optional[int],
        Field(default=None, ge=0, le=100_000_000, description="Expected call volume. Drives estimated_monthly_cost."),
    ] = None,
    expected_tokens: Annotated[
        Optional[int],
        Field(default=None, ge=0, le=1_000_000, description="Total tokens (input+output) per LLM call. Triggers exact per-token math for LLM providers."),
    ] = None,
    task_complexity: Annotated[
        Optional[TaskComplexity],
        Field(default=None, description="Task complexity hint for LLM model picker. low=Haiku/mini, very_high=Opus/4o."),
    ] = None,
    budget_strategy: Annotated[
        Optional[BudgetStrategy],
        Field(default=None, description="How to weigh reliability vs cost vs latency. Default: reliability_first (80/20)."),
    ] = None,
    eu_only: Annotated[
        Optional[bool],
        Field(default=None, description="Filter alternatives to EU-hosted only."),
    ] = None,
    gdpr_required: Annotated[
        Optional[bool],
        Field(default=None, description="Filter alternatives to GDPR-adequate jurisdictions."),
    ] = None,
    verbose: Annotated[
        Optional[bool],
        Field(default=False, description="Include extra fields (jurisdiction details, eu_alternatives, recommended_for) in the response."),
    ] = False,
) -> str:
    try:
        body, rate_limit = await api_request(
            method="POST",
            path="/v1/assess",
            body={
                "tool_identifier": tool_identifier,
                "context": context,
                "max_price_per_call": max_price_per_call,
                "max_monthly_budget": max_monthly_budget,
                "expected_calls_per_month": expected_calls_per_month,
                "expected_tokens": expected_tokens,
                "task_complexity": task_complexity,
                "budget_strategy": budget_strategy,
                "eu_only": eu_only,
                "gdpr_required": gdpr_required,
            },
        )
    except Exception as e:
        raise_tool_error(e)

    trimmed = _trim_response(body, verbose=bool(verbose))
    result: dict[str, Any] = {"summary": make_summary(body), **trimmed}
    if rate_limit is not None:
        result["_meta"] = {"rate_limit": rate_limit}
    return json.dumps(result, indent=2, default=_default)


def _trim_response(a: dict[str, Any], verbose: bool) -> dict[str, Any]:
    trend = a.get("trend")
    latency = a.get("latency")

    base: dict[str, Any] = {
        "reliability_score": a.get("reliability_score"),
        "confidence": a.get("confidence"),
        "data_source": a.get("data_source"),
        "historical_success_rate": a.get("historical_success_rate"),
        "predicted_failure_risk": a.get("predicted_failure_risk"),
        "trend": (
            {"direction": trend.get("direction"), "change_24h": trend.get("change_24h")}
            if isinstance(trend, dict)
            else None
        ),
        "common_pitfalls": [
            {
                "category": p.get("category"),
                "percentage": p.get("percentage"),
                "mitigation": p.get("mitigation"),
            }
            for p in (a.get("common_pitfalls") or [])
        ],
        "recommended_mitigations": a.get("recommended_mitigations") or [],
        "top_alternatives": a.get("top_alternatives") or [],
        "latency": (
            {"p50": latency.get("p50"), "p95": latency.get("p95"), "p99": latency.get("p99")}
            if isinstance(latency, dict)
            else None
        ),
        "hosting_jurisdiction": a.get("hosting_jurisdiction"),
        "gdpr_compliant": a.get("gdpr_compliant"),
        "data_residency_risk": a.get("data_residency_risk"),
        "price_per_call": a.get("price_per_call"),
        "pricing_model": a.get("pricing_model"),
        "cost_adjusted_score": a.get("cost_adjusted_score"),
        "estimated_monthly_cost": a.get("estimated_monthly_cost"),
        "within_budget": a.get("within_budget"),
        "budget_explanation": a.get("budget_explanation"),
        "recommended_model": a.get("recommended_model"),
        "reasoning": a.get("reasoning"),
        "last_updated": a.get("last_updated"),
    }

    if verbose:
        base["jurisdiction_source"] = a.get("jurisdiction_source")
        base["jurisdiction_confidence"] = a.get("jurisdiction_confidence")
        base["jurisdiction_notes"] = a.get("jurisdiction_notes")
        base["recommended_for"] = a.get("recommended_for") or []
        base["eu_alternatives"] = a.get("eu_alternatives") or []

    return base


def _default(obj: Any) -> Any:
    if isinstance(obj, dict):
        return dict(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serialisable")
