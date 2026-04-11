import secrets

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select, func

from app.dependencies import Db, AuthenticatedKey
from app.models.webhook import Webhook

router = APIRouter()


class WebhookCreate(BaseModel):
    url: HttpUrl = Field(..., description="HTTPS URL to receive webhook POST requests")
    event: str = Field("score.change", description="Event type (currently only 'score.change')")
    tool_identifier: str | None = Field(None, description="Only fire for this tool (omit for all tools)")
    threshold: int = Field(5, ge=1, le=50, description="Minimum score change (points) to trigger webhook")


class WebhookResponse(BaseModel):
    id: str
    url: str
    event: str
    tool_identifier: str | None
    threshold: int
    secret: str | None = Field(None, description="HMAC signing secret (only returned on creation)")
    is_active: bool


@router.post("/webhooks", tags=["Webhooks"],
             summary="Register a webhook",
             description="Register a URL to receive POST notifications when tool reliability scores change. "
                         "The signing secret is only returned once — store it securely.")
async def create_webhook(
    body: WebhookCreate,
    db: Db,
    api_key: AuthenticatedKey,
):
    # Limit webhooks per API key
    count = (await db.execute(
        select(func.count()).select_from(Webhook).where(
            Webhook.api_key_id == api_key.id, Webhook.is_active == True  # noqa: E712
        )
    )).scalar()
    if count >= 10:
        raise HTTPException(400, "Maximum 10 active webhooks per API key")

    if body.event != "score.change":
        raise HTTPException(400, f"Unsupported event type: {body.event}. Currently only 'score.change' is supported.")

    secret = secrets.token_hex(32)
    wh = Webhook(
        api_key_id=api_key.id,
        url=str(body.url),
        event=body.event,
        tool_identifier=body.tool_identifier,
        threshold=body.threshold,
        secret=secret,
    )
    db.add(wh)
    await db.commit()

    return WebhookResponse(
        id=str(wh.id),
        url=wh.url,
        event=wh.event,
        tool_identifier=wh.tool_identifier,
        threshold=wh.threshold,
        secret=secret,
        is_active=True,
    )


@router.get("/webhooks", tags=["Webhooks"],
            summary="List your webhooks",
            description="List all webhooks registered under your API key.")
async def list_webhooks(
    db: Db,
    api_key: AuthenticatedKey,
):
    result = await db.execute(
        select(Webhook).where(Webhook.api_key_id == api_key.id).order_by(Webhook.created_at.desc())
    )
    webhooks = result.scalars().all()
    return {
        "webhooks": [
            WebhookResponse(
                id=str(wh.id),
                url=wh.url,
                event=wh.event,
                tool_identifier=wh.tool_identifier,
                threshold=wh.threshold,
                is_active=wh.is_active,
            )
            for wh in webhooks
        ],
        "count": len(webhooks),
    }


@router.delete("/webhooks/{webhook_id}", tags=["Webhooks"],
               summary="Delete a webhook",
               description="Permanently delete a webhook registration.")
async def delete_webhook(
    webhook_id: str,
    db: Db,
    api_key: AuthenticatedKey,
):
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.api_key_id == api_key.id)
    )
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(404, "Webhook not found")

    await db.delete(wh)
    await db.commit()
    return {"status": "deleted"}
