"""
Webhook dispatch service.

When a tool's reliability score changes significantly, notify registered webhooks.
Dispatches are fire-and-forget via asyncio tasks to avoid blocking the request path.
"""
import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

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
    db: AsyncSession,
    tool_identifier: str,
    old_score: float,
    new_score: float,
):
    """Check if any webhooks should fire for this score change."""
    delta = abs(new_score - old_score)
    if delta < 1:
        return

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
        asyncio.create_task(_deliver(db, wh, payload))


async def _deliver(db: AsyncSession, webhook: Webhook, payload: dict):
    """Deliver a single webhook. Deactivate after 10 consecutive failures."""
    body = json.dumps(payload).encode()
    signature = sign_payload(body, webhook.secret)

    try:
        client = _get_client()
        resp = await client.post(
            webhook.url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-NemoFlow-Signature": signature,
                "X-NemoFlow-Event": payload["event"],
            },
        )
        if resp.status_code < 300:
            webhook.failure_count = 0
            webhook.last_triggered_at = datetime.now(timezone.utc)
        else:
            webhook.failure_count += 1
            logger.warning("Webhook %s returned %s", webhook.id, resp.status_code)
    except Exception as e:
        webhook.failure_count += 1
        logger.warning("Webhook %s delivery failed: %s", webhook.id, e)

    if webhook.failure_count >= 10:
        webhook.is_active = False
        logger.info("Webhook %s deactivated after 10 failures", webhook.id)

    await db.commit()
