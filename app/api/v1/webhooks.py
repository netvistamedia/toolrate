import ipaddress
import secrets
import socket
import uuid as _uuid
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl, field_validator
from sqlalchemy import select, func

from app.dependencies import Db, AuthenticatedKey
from app.models.webhook import Webhook

router = APIRouter()

# IP ranges that must be blocked for webhook URLs (SSRF prevention).
# These cover every RFC1918 private block, loopback (v4 and v6), link-local,
# and the cloud metadata ranges that AWS/GCP/Azure expose on 169.254.169.254.
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # "this network" / unspecified
    ipaddress.ip_network("10.0.0.0/8"),         # Private
    ipaddress.ip_network("100.64.0.0/10"),      # Carrier-grade NAT
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local / cloud metadata
    ipaddress.ip_network("172.16.0.0/12"),      # Private
    ipaddress.ip_network("192.0.0.0/24"),       # IETF protocol assignments
    ipaddress.ip_network("192.168.0.0/16"),     # Private
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmarking
    ipaddress.ip_network("::1/128"),            # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),           # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),          # IPv6 link-local
    ipaddress.ip_network("::ffff:0:0/96"),      # IPv4-mapped IPv6 (SSRF vector)
]

# Hostnames that should never be allowed regardless of how they resolve —
# the cloud-metadata hosts in particular can serve credentials on 169.254.169.254.
_BLOCKED_HOSTNAMES = frozenset({
    "localhost",
    "0.0.0.0",
    "metadata",
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
    "instance-data.ec2.internal",
})


def _ip_is_blocked(addr: ipaddress._BaseAddress) -> bool:
    return any(addr in net for net in _BLOCKED_NETWORKS)


def _resolve_hostname(hostname: str) -> list[ipaddress._BaseAddress]:
    """Return every A/AAAA record for `hostname`, empty on failure.

    Uses a blocking getaddrinfo. That's acceptable because this runs inside
    a Pydantic validator on the (low-volume) webhook-registration path.
    """
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return []
    out: list[ipaddress._BaseAddress] = []
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip_str = sockaddr[0]
        try:
            out.append(ipaddress.ip_address(ip_str))
        except ValueError:
            continue
    return out


def _is_public_url(url: str) -> bool:
    """Reject URLs that would let a user probe internal infrastructure.

    Strategy:
      1. Reject obvious internal hostnames (localhost, metadata endpoints).
      2. If the host is a literal IP, reject anything in `_BLOCKED_NETWORKS`.
      3. Otherwise resolve the hostname NOW and reject if *any* resolved IP
         is blocked. A hostname that currently resolves publicly but later
         flips to an internal IP (DNS rebinding) is not defended against at
         this layer — mitigate that with an outbound egress policy.
    """
    parsed = urlparse(str(url))
    hostname = parsed.hostname
    if not hostname:
        return False
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        return False

    # Literal IP — check directly.
    try:
        addr = ipaddress.ip_address(hostname)
        return not _ip_is_blocked(addr)
    except ValueError:
        pass

    # Hostname — resolve and reject if any record is blocked. A hostname
    # that fails DNS entirely is also rejected: we'd rather force the user
    # to register a real URL than silently accept a dead endpoint.
    resolved = _resolve_hostname(hostname)
    if not resolved:
        return False
    return all(not _ip_is_blocked(ip) for ip in resolved)


class WebhookCreate(BaseModel):
    url: HttpUrl = Field(..., description="HTTPS URL to receive webhook POST requests")
    event: str = Field("score.change", description="Event type (currently only 'score.change')")
    tool_identifier: str | None = Field(None, description="Only fire for this tool (omit for all tools)")
    threshold: int = Field(5, ge=1, le=50, description="Minimum score change (points) to trigger webhook")

    @field_validator("url")
    @classmethod
    def url_must_be_public(cls, v):
        if not _is_public_url(str(v)):
            raise ValueError("Webhook URL must point to a publicly accessible address")
        if not str(v).startswith("https://"):
            raise ValueError("Webhook URL must use HTTPS")
        return v


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
        raise HTTPException(422, "Maximum 10 active webhooks per API key")

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
    from app.services.audit import log_audit
    await log_audit(db, "webhook_created", actor_key_prefix=api_key.key_prefix,
                    resource_type="webhook", resource_id=str(wh.id),
                    detail={"url": str(body.url), "event": body.event})
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
    try:
        wh_uuid = _uuid.UUID(webhook_id)
    except ValueError:
        raise HTTPException(404, "Webhook not found")

    result = await db.execute(
        select(Webhook).where(Webhook.id == wh_uuid, Webhook.api_key_id == api_key.id)
    )
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(404, "Webhook not found")

    await db.delete(wh)
    await db.commit()
    return {"status": "deleted"}
