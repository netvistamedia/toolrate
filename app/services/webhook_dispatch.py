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

from app.models.webhook import Webhook

logger = logging.getLogger("nemoflow.webhooks")

_client: httpx.AsyncClient | None = None


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
        asyncio.create_task(_deliver(wh.id, wh.url, wh.secret, payload))


async def _deliver(webhook_id, url: str, secret: str, payload: dict):
    """Deliver a single webhook. Deactivate after 10 consecutive failures.
    Uses its own DB session for updates."""
    from app.db.session import async_session

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
                "X-NemoFlow-Signature": signature,
                "X-NemoFlow-Event": payload["event"],
            },
        )
        success = resp.status_code < 300
        if not success:
            logger.warning("Webhook %s returned %s", webhook_id, resp.status_code)
    except Exception as e:
        logger.warning("Webhook %s delivery failed: %s", webhook_id, e)

    async with async_session() as db:
        if success:
            await db.execute(
                update(Webhook)
                .where(Webhook.id == webhook_id)
                .values(failure_count=0, last_triggered_at=datetime.now(timezone.utc))
            )
        else:
            # Increment failure count and deactivate if >= 10 in a single atomic UPDATE
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
