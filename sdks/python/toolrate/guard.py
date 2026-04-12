"""ToolRate Guard — one-line reliability wrapper for tool calls.

Usage:
    from toolrate import ToolRate, guard

    client = ToolRate("nf_live_...")

    # Wrap any tool call — assess before, report after
    result = guard(client, "https://api.openai.com/v1/chat/completions",
                   lambda: openai.chat.completions.create(...))

    # Explicit fallbacks — tries each in order on failure
    result = guard(client, "https://api.openai.com/v1/chat/completions",
                   lambda: openai.chat.completions.create(...),
                   fallbacks=[
                       ("https://api.anthropic.com/v1/messages",
                        lambda: anthropic.messages.create(...)),
                   ])

    # Dynamic (auto) fallbacks — ToolRate picks from real agent journey data
    result = guard(client, "https://api.openai.com/v1/chat/completions",
                   lambda: openai.chat.completions.create(...),
                   fallbacks="auto",
                   resolvers={
                       "https://api.anthropic.com/v1/messages":
                           lambda: anthropic.messages.create(...),
                       "https://api.groq.com/openai/v1/chat/completions":
                           lambda: groq_client.chat.completions.create(...),
                   })

    # As a decorator
    @toolrate_guard(client, "https://api.stripe.com/v1/charges")
    def charge_customer(amount, currency):
        return stripe.Charge.create(amount=amount, currency=currency)
"""

from __future__ import annotations

import time
import uuid
from functools import wraps
from typing import Any, Callable, Literal, TypeVar, Union

from toolrate.client import ToolRate

T = TypeVar("T")

Fallbacks = Union[list[tuple[str, Callable[[], T]]], Literal["auto"], None]


def guard(
    client: ToolRate,
    tool_identifier: str,
    fn: Callable[[], T],
    *,
    context: str = "",
    min_score: float = 0.0,
    fallbacks: Fallbacks = None,
    resolvers: dict[str, Callable[[], T]] | None = None,
    max_fallbacks: int = 3,
) -> T:
    """Execute a tool call with ToolRate reliability guard.

    1. Assesses the tool's reliability score
    2. If score < min_score and fallbacks exist, tries the best-scoring fallback
    3. Executes the tool call
    4. Reports success/failure back to ToolRate
    5. On failure with fallbacks, automatically tries the next option

    Args:
        client: ToolRate instance
        tool_identifier: The tool's API identifier
        fn: The actual tool call to execute (as a callable)
        context: Workflow context for context-bucketed scoring
        min_score: Minimum reliability score to proceed (0-100). Default 0 = always try.
        fallbacks: Either a list of (tool_identifier, callable) pairs, or the string
            "auto" to have ToolRate pick fallbacks dynamically from the primary tool's
            top alternatives and real fallback-chain data. "auto" requires `resolvers`.
        resolvers: Mapping of tool identifier → callable. When `fallbacks="auto"`,
            ToolRate matches candidate alternatives against these keys and only tries
            tools the caller has pre-registered a runner for.
        max_fallbacks: Max number of auto fallbacks to include (default 3).

    Returns:
        The result of the successful tool call

    Raises:
        The exception from the last failed tool call if all options are exhausted
    """
    session_id = uuid.uuid4().hex[:16]

    if fallbacks == "auto":
        explicit_fallbacks: list[tuple[str, Callable[[], T]]] = []
        auto_mode = True
    else:
        explicit_fallbacks = list(fallbacks or [])
        auto_mode = False

    all_tools: list[tuple[str, Callable[[], T]]] = [(tool_identifier, fn)] + explicit_fallbacks

    last_error: Exception | None = None
    i = 0
    while i < len(all_tools):
        attempt = i + 1
        ident, call = all_tools[i]

        # Assess
        assessment: dict[str, Any] | None = None
        try:
            assessment = client.assess(ident, context=context)
            score = assessment.get("reliability_score", 100)
        except Exception:
            score = 100  # If assess fails, don't block the tool call

        # Resolve auto fallbacks once, using the primary tool's assessment (no extra API call if it has alternatives)
        if auto_mode and i == 0:
            auto_tools = _resolve_auto_fallbacks(
                client, ident, assessment, resolvers or {}, max_fallbacks
            )
            all_tools.extend(auto_tools)
            auto_mode = False

        # Skip if score too low and we have more options
        if score < min_score and attempt < len(all_tools):
            _safe_report(
                client, ident, success=False, error_category="skipped_low_score",
                context=context, session_id=session_id, attempt_number=attempt,
                previous_tool=all_tools[i - 1][0] if i > 0 else None,
            )
            i += 1
            continue

        # Execute
        start = time.perf_counter()
        try:
            result = call()
            latency_ms = int((time.perf_counter() - start) * 1000)

            _safe_report(
                client, ident, success=True, latency_ms=latency_ms,
                context=context, session_id=session_id, attempt_number=attempt,
                previous_tool=all_tools[i - 1][0] if i > 0 else None,
            )
            return result

        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            last_error = e

            _safe_report(
                client, ident, success=False, error_category=_classify_error(e),
                latency_ms=latency_ms, context=context, session_id=session_id,
                attempt_number=attempt,
                previous_tool=all_tools[i - 1][0] if i > 0 else None,
            )

            if attempt >= len(all_tools):
                raise
            i += 1

    raise last_error  # type: ignore[misc]


def toolrate_guard(
    client: ToolRate,
    tool_identifier: str,
    *,
    context: str = "",
    min_score: float = 0.0,
    fallbacks: Fallbacks = None,
    resolvers: dict[str, Callable[[], Any]] | None = None,
    max_fallbacks: int = 3,
):
    """Decorator version of guard.

    Usage:
        @toolrate_guard(client, "https://api.stripe.com/v1/charges")
        def charge(amount, currency):
            return stripe.Charge.create(amount=amount, currency=currency)
    """
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return guard(
                client, tool_identifier,
                lambda: fn(*args, **kwargs),
                context=context, min_score=min_score,
                fallbacks=fallbacks, resolvers=resolvers,
                max_fallbacks=max_fallbacks,
            )
        return wrapper
    return decorator


def _resolve_auto_fallbacks(
    client: ToolRate,
    primary_identifier: str,
    primary_assessment: dict[str, Any] | None,
    resolvers: dict[str, Callable[[], Any]],
    max_n: int,
) -> list[tuple[str, Callable[[], Any]]]:
    """Pick fallback callables by matching ToolRate's alternatives against user resolvers."""
    if not resolvers or max_n <= 0:
        return []

    candidates: list[str] = []

    # 1. Reuse top_alternatives from the assessment we already fetched (no extra API call)
    if primary_assessment:
        for alt in primary_assessment.get("top_alternatives") or []:
            if isinstance(alt, dict) and alt.get("tool"):
                candidates.append(alt["tool"])

    # 2. If no alternatives in assess response, query fallback-chain endpoint
    if not candidates:
        try:
            chain_resp = client.discover_fallback_chain(primary_identifier)
            for item in chain_resp.get("fallback_chain") or []:
                if isinstance(item, dict) and item.get("fallback_tool"):
                    candidates.append(item["fallback_tool"])
        except Exception:
            pass

    out: list[tuple[str, Callable[[], Any]]] = []
    seen: set[str] = {primary_identifier}
    for ident in candidates:
        if ident in seen:
            continue
        runner = resolvers.get(ident)
        if runner is None:
            continue
        out.append((ident, runner))
        seen.add(ident)
        if len(out) >= max_n:
            break

    return out


def _safe_report(client: ToolRate, tool_identifier: str, **kwargs: Any) -> None:
    """Fire-and-forget reporting. Never fail the user's tool call because reporting failed."""
    try:
        client.report(tool_identifier, **kwargs)
    except Exception:
        pass


def _classify_error(error: Exception) -> str:
    """Best-effort classification of an exception into ToolRate error categories."""
    name = type(error).__name__.lower()
    message = str(error).lower()

    if "timeout" in name or "timeout" in message or "timed out" in message:
        return "timeout"
    if "ratelimit" in name or "rate" in message and "limit" in message or "429" in message or "too many" in message:
        return "rate_limit"
    if "auth" in name or "unauthorized" in message or "403" in message or "401" in message:
        return "auth_failure"
    if "validation" in name or "invalid" in message or "422" in message:
        return "validation_error"
    if "notfound" in name or "not found" in message or "404" in message:
        return "not_found"
    if "permission" in name or "forbidden" in message:
        return "permission_denied"
    if "connect" in name or "connection" in message or "dns" in message:
        return "connection_error"

    return "server_error"
