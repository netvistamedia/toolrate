"""
Webhook dispatch service.

When a tool's reliability score changes significantly, notify registered webhooks.
Dispatches are fire-and-forget via asyncio tasks with their own DB sessions.
"""
import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import case, select, or_, update

from app.core.url_safety import is_public_url
from app.models.webhook import Webhook

logger = logging.getLogger("nemoflow.webhooks")

_client: httpx.AsyncClient | None = None

# Strong references to in-flight deliveries. Without this the `task` local
# goes out of scope on the next loop iteration and asyncio's weak-ref GC can
# collect the task mid-delivery — the done_callback below is attached to the
# Task object itself, so it vanishes with it.
_pending_deliveries: set[asyncio.Task] = set()


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=10.0)
    return _client


def sign_payload(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def dispatch_score_change(
    tool_identifier: str,
    old_score: float,
    new_score: float,
):
    """Check if any webhooks should fire for this score change.
    Uses its own DB session to avoid request-scoped session lifecycle issues."""
    from app.db.session import async_session

    delta = abs(new_score - old_score)
    if delta < 1:
        return

    async with async_session() as db:
        stmt = select(Webhook).where(
            Webhook.is_active == True,  # noqa: E712
            Webhook.event == "score.change",
            Webhook.threshold <= delta,
            or_(
                Webhook.tool_identifier.is_(None),
                Webhook.tool_identifier == tool_identifier,
            ),
        )
        result = await db.execute(stmt)
        webhooks = result.scalars().all()

    if not webhooks:
        return

    payload = {
        "event": "score.change",
        "tool_identifier": tool_identifier,
        "old_score": round(old_score, 2),
        "new_score": round(new_score, 2),
        "delta": round(new_score - old_score, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    for wh in webhooks:
        task = asyncio.create_task(_deliver(wh.id, wh.url, wh.secret, payload))
        _pending_deliveries.add(task)
        task.add_done_callback(_log_task_exception)


def _log_task_exception(task: "asyncio.Task") -> None:
    """Surface background-task failures AND release the strong reference.

    Without the discard, `_pending_deliveries` grows without bound. Without
    the logging, exceptions raised inside `_deliver` (e.g. a DB outage while
    updating failure_count) are only emitted as an asyncio "task exception
    never retrieved" warning at GC time.
    """
    _pending_deliveries.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error("Webhook delivery task crashed: %s", exc, exc_info=exc)


async def _record_delivery_result(webhook_id, success: bool) -> None:
    """Persist the success/failure outcome of a single delivery attempt.

    On success: clear ``failure_count`` and stamp ``last_triggered_at``.
    On failure: atomically increment ``failure_count`` and deactivate the
    webhook when the new count reaches 10. The single UPDATE avoids a
    race where two concurrent deliveries to the same webhook both read
    ``failure_count == 9`` and each only bump to 10, instead of one
    reaching 11 and the deactivation never triggering cleanly.

    This is a shared sink so every failure path — real HTTP failure, SSRF
    revalidation rejection, timeout — routes through the same counter
    bump and deactivation rule.
    """
    from app.db.session import async_session

    async with async_session() as db:
        if success:
            await db.execute(
                update(Webhook)
                .where(Webhook.id == webhook_id)
                .values(
                    failure_count=0,
                    last_triggered_at=datetime.now(timezone.utc),
                )
            )
        else:
            await db.execute(
                update(Webhook)
                .where(Webhook.id == webhook_id)
                .values(
                    failure_count=Webhook.failure_count + 1,
                    is_active=case(
                        (Webhook.failure_count + 1 >= 10, False),
                        else_=Webhook.is_active,
                    ),
                )
            )
        await db.commit()


async def _deliver(webhook_id, url: str, secret: str, payload: dict):
    """Deliver a single webhook. Deactivate after 10 consecutive failures.

    Runs an SSRF revalidation step *before* every POST: ``is_public_url``
    is called again with the stored URL so that a hostname which resolved
    publicly at registration but has since been flipped to an internal
    address (DNS rebinding, domain takeover, compromised DNS) is rejected
    at delivery time instead of leaking an HTTP request to a private
    target. Rejected deliveries count as failures and flow through the
    same auto-deactivation path as any other flaky endpoint.
    """
    # Defense against DNS rebinding + domain takeover: re-validate the URL
    # on every delivery. `is_public_url` resolves the hostname now, so an
    # attacker who flips DNS between registration and delivery still fails
    # the check. The tiny residual TOCTOU window (between this call and
    # the socket connect inside httpx) is acceptable — a practical rebind
    # attack needs sub-millisecond DNS timing AND a short TTL, while the
    # blast radius of a single blind SSRF POST without response-body
    # reflection is already small.
    if not is_public_url(url):
        logger.warning(
            "Webhook %s delivery blocked: url %s failed SSRF revalidation "
            "(possible DNS rebinding or domain takeover)",
            webhook_id, url,
        )
        await _record_delivery_result(webhook_id, success=False)
        return

    body = json.dumps(payload).encode()
    signature = sign_payload(body, secret)
    success = False

    try:
        client = _get_client()
        resp = await client.post(
            url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-ToolRate-Signature": signature,
                "X-ToolRate-Event": payload["event"],
            },
            # Explicit defense-in-depth: httpx already defaults to False,
            # but pinning it here prevents a silent behaviour change if
            # an upstream version ever flips the default. A 302 from
            # attacker.com → http://169.254.169.254/latest/meta-data/
            # would otherwise hit cloud metadata despite the SSRF check.
            follow_redirects=False,
        )
        success = resp.status_code < 300
        if not success:
            logger.warning("Webhook %s returned %s", webhook_id, resp.status_code)
    except Exception as e:
        logger.warning("Webhook %s delivery failed: %s", webhook_id, e)

    await _record_delivery_result(webhook_id, success)
