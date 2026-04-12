"""Lightweight audit logging for sensitive operations."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_audit(
    db: AsyncSession,
    action: str,
    *,
    actor_key_prefix: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: dict[str, Any] | None = None,
    client_ip: str | None = None,
) -> None:
    """Write an audit log entry. Fire-and-forget — never raises."""
    try:
        db.add(AuditLog(
            action=action,
            actor_key_prefix=actor_key_prefix,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            client_ip=client_ip,
        ))
        # Don't commit here — caller owns the transaction
    except Exception:
        pass  # Audit logging must never break the request
