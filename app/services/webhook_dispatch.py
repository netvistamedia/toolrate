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
from app.models.audit_log import AuditLog
from app.models.webhook import Webhook

logger = logging.getLogger("nemoflow.webhooks")

_client: httpx.AsyncClient | None = None

# Strong references to in-flight deliveries. Without this the `task` local
# goes out of scope on the next loop iteration and asyncio's weak-ref GC can
# collect the task mid-delivery — the done_callback below is attached to the
# Task object itself, so it vanishes with it.
_pending_deliveries: set[asyncio.Task] = set()

# Backoff schedule between retry attempts, in seconds. With three values we
# get four total attempts (one immediate + three retries with these delays).
# Module-level so tests can monkeypatch this to ``(0, 0, 0)`` and avoid 36s
# of real sleeping per failed delivery. Values: 1s for the common transient
# blip, 5s for short outages, 30s as a last gasp before giving up — total
# wall-clock 36s, comparable to Stripe's own retry cadence.
RETRY_BACKOFFS_SEC: tuple[float, ...] = (1.0, 5.0, 30.0)

# Deactivate after this many consecutive failed deliveries. Each "delivery"
# already includes the retry chain above, so 10 strikes ≈ 40 attempts spread
# over many score-change events, never a tight loop.
AUTO_DEACTIVATE_AFTER = 10


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


async def _record_delivery_result(
    webhook_id, success: bool, *, last_error: str | None = None,
) -> None:
    """Persist the success/failure outcome of a single delivery attempt.

    On success: clear ``failure_count`` and stamp ``last_triggered_at``.
    On failure: atomically increment ``failure_count`` and deactivate the
    webhook when the new count reaches ``AUTO_DEACTIVATE_AFTER``. The single
    UPDATE avoids a race where two concurrent deliveries to the same webhook
    both read ``failure_count == 9`` and each only bump to 10, instead of
    one reaching 11 and the deactivation never triggering cleanly.

    When this delivery is the one that crosses the deactivation threshold,
    we additionally:

    1. Write a ``webhook_auto_disabled`` audit log row so admins can see
       silently-deactivated endpoints in the dashboard.
    2. Email the owner if they set ``notification_email`` at registration —
       previously a deactivation was completely silent.

    This is a shared sink so every failure path — real HTTP failure, SSRF
    revalidation rejection, timeout — routes through the same counter
    bump, deactivation rule, and notification path.
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
            await db.commit()
            return

        await db.execute(
            update(Webhook)
            .where(Webhook.id == webhook_id)
            .values(
                failure_count=Webhook.failure_count + 1,
                is_active=case(
                    (
                        Webhook.failure_count + 1 >= AUTO_DEACTIVATE_AFTER,
                        False,
                    ),
                    else_=Webhook.is_active,
                ),
            )
        )
        await db.commit()

        # Detect the exact transition: this delivery just pushed failure_count
        # to AUTO_DEACTIVATE_AFTER and flipped is_active False. Concurrent
        # deliveries that arrive after the flip would land on
        # failure_count == AUTO_DEACTIVATE_AFTER + 1, +2, ... so only the
        # delivery that actually disabled the webhook hits this branch.
        wh = (
            await db.execute(select(Webhook).where(Webhook.id == webhook_id))
        ).scalar_one_or_none()
        if (
            wh is not None
            and wh.is_active is False
            and wh.failure_count == AUTO_DEACTIVATE_AFTER
        ):
            await _on_webhook_auto_deactivated(db, wh, last_error=last_error)


async def _on_webhook_auto_deactivated(
    db, webhook: Webhook, *, last_error: str | None
) -> None:
    """Audit + notify when a webhook crossed the auto-deactivate threshold.

    Both side effects are best-effort: a failure here must not raise out of
    the dispatch task or it would be re-logged as a generic "delivery task
    crashed" error. Audit log is committed in the same session as the
    deactivation update so an external dashboard sees them together.
    """
    try:
        db.add(
            AuditLog(
                action="webhook_auto_disabled",
                resource_type="webhook",
                resource_id=str(webhook.id),
                detail={
                    "url": webhook.url,
                    "failure_count": webhook.failure_count,
                    "last_error": (last_error or "")[:300] or None,
                },
            )
        )
        await db.commit()
    except Exception as e:
        logger.warning("Failed to write webhook_auto_disabled audit row: %s", e)

    if webhook.notification_email:
        # Lazy import keeps ``app.services.email`` outside this module's
        # import-time graph so unit tests can stub it without dragging in
        # the SendGrid client.
        from app.services.email import send_webhook_deactivated_email

        try:
            await send_webhook_deactivated_email(
                webhook.notification_email,
                webhook_url=webhook.url,
                failure_count=webhook.failure_count,
                last_error=last_error,
            )
        except Exception as e:
            logger.warning(
                "Webhook deactivation email failed for %s: %s",
                webhook.id, e,
            )


async def _deliver(webhook_id, url: str, secret: str, payload: dict):
    """Deliver a single webhook. Retry transient failures, deactivate after
    ``AUTO_DEACTIVATE_AFTER`` consecutive failed deliveries.

    Each delivery runs up to ``len(RETRY_BACKOFFS_SEC) + 1`` attempts. The
    classes of outcome:

    * **2xx** → success, returns immediately and clears the failure counter.
    * **5xx / network exception / timeout** → retryable. Sleep the next
      backoff and try again. After the last attempt, count one strike.
    * **4xx (other than 408/429)** → permanent caller error. Don't retry,
      count one strike — the customer's endpoint is misconfigured and
      retries won't help.
    * **SSRF revalidation rejection** → fail-fast, no retries. The URL is
      currently pointing inside; retrying inside a few seconds won't
      change that and we don't want to spend the time.

    Runs an SSRF revalidation step *before* every attempt: ``is_public_url``
    is called again so that a hostname which was public at registration
    but has since been flipped to an internal address (DNS rebinding,
    domain takeover, compromised DNS) is rejected at delivery time
    instead of leaking an HTTP request to a private target.
    """
    body = json.dumps(payload).encode()
    signature = sign_payload(body, secret)
    headers = {
        "Content-Type": "application/json",
        "X-ToolRate-Signature": signature,
        "X-ToolRate-Event": payload["event"],
    }

    success = False
    last_error: str | None = None
    max_attempts = len(RETRY_BACKOFFS_SEC) + 1

    for attempt in range(max_attempts):
        if attempt > 0:
            await asyncio.sleep(RETRY_BACKOFFS_SEC[attempt - 1])

        # Defense against DNS rebinding + domain takeover: re-validate the
        # URL on every attempt. `is_public_url` resolves the hostname now,
        # so an attacker who flips DNS between registration and delivery
        # still fails the check. SSRF rejection is treated as fatal — no
        # further retries, since the URL pointing inside is a property of
        # the endpoint, not a transient condition.
        if not is_public_url(url):
            last_error = (
                "ssrf_revalidation_failed (possible DNS rebinding or domain takeover)"
            )
            logger.warning(
                "Webhook %s delivery blocked: %s url=%s",
                webhook_id, last_error, url,
            )
            break

        try:
            client = _get_client()
            resp = await client.post(
                url,
                content=body,
                headers=headers,
                # Explicit defense-in-depth: httpx already defaults to False,
                # but pinning it here prevents a silent behaviour change if
                # an upstream version ever flips the default. A 302 from
                # attacker.com → http://169.254.169.254/latest/meta-data/
                # would otherwise hit cloud metadata despite the SSRF check.
                follow_redirects=False,
            )
            if resp.status_code < 300:
                success = True
                break
            last_error = f"http_{resp.status_code}"
            logger.warning(
                "Webhook %s attempt %d/%d returned %s",
                webhook_id, attempt + 1, max_attempts, resp.status_code,
            )
            if 400 <= resp.status_code < 500 and resp.status_code not in (408, 429):
                # Permanent caller error — bail out of the retry loop.
                # 408 (request timeout) and 429 (rate limit) are still
                # retryable: the receiver may recover.
                break
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            logger.warning(
                "Webhook %s attempt %d/%d failed: %s",
                webhook_id, attempt + 1, max_attempts, e,
            )

    await _record_delivery_result(webhook_id, success, last_error=last_error)
