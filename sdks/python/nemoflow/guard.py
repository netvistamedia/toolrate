"""NemoFlow Guard — one-line reliability wrapper for tool calls.

Usage:
    from nemoflow import NemoFlowClient, guard

    client = NemoFlowClient("nf_live_...")

    # Wrap any tool call — assess before, report after, auto-fallback
    result = guard(client, "https://api.openai.com/v1/chat/completions",
                   lambda: openai.chat.completions.create(...))

    # With fallbacks — tries alternatives if primary scores too low
    result = guard(client, "https://api.openai.com/v1/chat/completions",
                   lambda: openai.chat.completions.create(...),
                   fallbacks=[
                       ("https://api.anthropic.com/v1/messages",
                        lambda: anthropic.messages.create(...)),
                   ])

    # As a decorator
    @nemoflow_guard(client, "https://api.stripe.com/v1/charges")
    def charge_customer(amount, currency):
        return stripe.Charge.create(amount=amount, currency=currency)
"""

from __future__ import annotations

import time
import uuid
from functools import wraps
from typing import Any, Callable, TypeVar

from nemoflow.client import NemoFlowClient

T = TypeVar("T")


def guard(
    client: NemoFlowClient,
    tool_identifier: str,
    fn: Callable[[], T],
    *,
    context: str = "",
    min_score: float = 0.0,
    fallbacks: list[tuple[str, Callable[[], T]]] | None = None,
) -> T:
    """Execute a tool call with NemoFlow reliability guard.

    1. Assesses the tool's reliability score
    2. If score < min_score and fallbacks exist, tries the best-scoring fallback
    3. Executes the tool call
    4. Reports success/failure back to NemoFlow
    5. On failure with fallbacks, automatically tries the next option

    Args:
        client: NemoFlowClient instance
        tool_identifier: The tool's API identifier
        fn: The actual tool call to execute (as a callable)
        context: Workflow context for context-bucketed scoring
        min_score: Minimum reliability score to proceed (0-100). Default 0 = always try.
        fallbacks: List of (tool_identifier, callable) pairs to try on failure

    Returns:
        The result of the successful tool call

    Raises:
        The exception from the last failed tool call if all options are exhausted
    """
    session_id = uuid.uuid4().hex[:16]
    all_tools = [(tool_identifier, fn)] + (fallbacks or [])

    last_error = None

    for attempt, (ident, call) in enumerate(all_tools, start=1):
        # Assess
        try:
            assessment = client.assess(ident, context=context)
            score = assessment.get("reliability_score", 100)
        except Exception:
            score = 100  # If assess fails, don't block the tool call

        # Skip if score too low and we have more options
        if score < min_score and attempt < len(all_tools):
            client.report(
                ident, success=False, error_category="skipped_low_score",
                context=context, session_id=session_id,
                attempt_number=attempt,
                previous_tool=all_tools[attempt - 2][0] if attempt > 1 else None,
            )
            continue

        # Execute
        start = time.perf_counter()
        try:
            result = call()
            latency_ms = int((time.perf_counter() - start) * 1000)

            # Report success
            client.report(
                ident, success=True, latency_ms=latency_ms,
                context=context, session_id=session_id,
                attempt_number=attempt,
                previous_tool=all_tools[attempt - 2][0] if attempt > 1 else None,
            )
            return result

        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            last_error = e

            # Classify error
            error_category = _classify_error(e)

            # Report failure
            client.report(
                ident, success=False, error_category=error_category,
                latency_ms=latency_ms, context=context,
                session_id=session_id, attempt_number=attempt,
                previous_tool=all_tools[attempt - 2][0] if attempt > 1 else None,
            )

            # If no more fallbacks, raise
            if attempt >= len(all_tools):
                raise

    # Should not reach here, but just in case
    raise last_error  # type: ignore


def nemoflow_guard(
    client: NemoFlowClient,
    tool_identifier: str,
    *,
    context: str = "",
    min_score: float = 0.0,
):
    """Decorator version of guard.

    Usage:
        @nemoflow_guard(client, "https://api.stripe.com/v1/charges")
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
            )
        return wrapper
    return decorator


def _classify_error(error: Exception) -> str:
    """Best-effort classification of an exception into NemoFlow error categories."""
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
