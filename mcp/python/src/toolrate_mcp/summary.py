"""Build the ``summary`` block for assess responses.

Mirrors ``mcp/typescript/src/summary.ts`` byte-for-byte so Python and TS
clients see the same one-liner for the same assess payload.
"""
from __future__ import annotations

from typing import Any


def make_summary(a: dict[str, Any]) -> dict[str, Any]:
    score = round(a.get("reliability_score", 0))
    recommended = score >= 70 and a.get("within_budget") is not False
    return {
        "reliability_score": score,
        "confidence": _round2(float(a.get("confidence") or 0)),
        "recommended": recommended,
        "one_liner": _one_liner(a, score, recommended),
    }


def _one_liner(a: dict[str, Any], score: int, recommended: bool) -> str:
    headline = _score_label(score, a.get("data_source", ""))
    tags: list[str] = []

    within_budget = a.get("within_budget")
    if within_budget is True:
        tags.append("within budget")
    elif within_budget is False:
        tags.append("OVER budget")

    if a.get("recommended_model"):
        tags.append(f"use {a['recommended_model']}")

    gdpr = a.get("gdpr_compliant")
    residency = a.get("data_residency_risk")
    if gdpr is True:
        tags.append("GDPR-compliant")
    elif gdpr is False and residency and residency != "none":
        tags.append(f"{residency} data-residency risk")

    tagged = f"{headline} — {', '.join(tags)}" if tags else headline
    suffix = "Safe to proceed." if recommended else "Consider an alternative from top_alternatives."
    return f"{tagged}. {suffix}"


def _score_label(score: int, data_source: str) -> str:
    if score >= 90:
        label = f"Highly reliable ({score}/100)"
    elif score >= 70:
        label = f"Reliable ({score}/100)"
    elif score >= 50:
        label = f"Moderately reliable ({score}/100)"
    else:
        label = f"Low reliability ({score}/100)"

    if data_source == "llm_estimated":
        label += ", LLM-estimated"
    elif data_source == "bayesian_prior":
        label += ", limited data"
    return label


def _round2(n: float) -> float:
    return round(n * 100) / 100
