"""Customer-facing account & usage dashboard.

Any authenticated API key can call `/v1/me/dashboard` — the response is
scoped to that key alone: current-period quota, 30-day usage history (read
from the per-key daily counter the PAYG meter already maintains), and a
billing snapshot tailored to the caller's tier.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from app.config import settings
from app.dependencies import AuthenticatedKey, Db, RedisClient
from app.services.rate_limiter import current_usage

router = APIRouter()


NEAR_LIMIT_PCT = 80.0


def _start_of_next_period(now: datetime, period: str) -> datetime:
    if period == "monthly":
        if now.month == 12:
            return datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        return datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return tomorrow


async def _read_daily_history(redis, key_hash: str, days: int = 30) -> list[dict]:
    """Read `assess:{hash}:{YYYY-MM-DD}` counters for the last `days` days.

    The PAYG meter writes these on every `/v1/assess` call with a 35-day TTL
    (see `app/services/payg_meter.py`), so a 30-day window is always covered.
    Missing days are returned as zero so the frontend can draw a complete
    sparkline without having to fill gaps itself.
    """
    today = datetime.now(timezone.utc).date()
    out: list[dict] = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        raw = await redis.get(f"assess:{key_hash}:{day.isoformat()}")
        out.append({"date": day.isoformat(), "count": int(raw) if raw else 0})
    return out


def _upgrade_hint(tier: str, percent_used: float, payg_billable_mtd: int) -> dict:
    if tier == "free" and percent_used >= NEAR_LIMIT_PCT:
        return {
            "suggested_plan": "payg",
            "reason": (
                "You're approaching the free daily cap. Pay-as-you-go keeps "
                "your first 100 assessments free every day and bills only the "
                "overage at $0.008 each."
            ),
        }
    if tier == "payg" and payg_billable_mtd >= 1000:
        # At ~1000 billable calls/month ($8), Pro's flat $29/mo for 10,000
        # becomes the better deal before long.
        return {
            "suggested_plan": "pro",
            "reason": (
                "At your current overage volume, the Pro plan's flat "
                "$29/month for 10,000 assessments is usually cheaper."
            ),
        }
    if tier == "pro" and percent_used >= NEAR_LIMIT_PCT:
        return {
            "suggested_plan": "enterprise",
            "reason": (
                "You're using most of your monthly Pro quota. Enterprise "
                "lifts the cap and adds private data pools."
            ),
        }
    return {"suggested_plan": None, "reason": None}


@router.get(
    "/me/dashboard",
    tags=["Stats"],
    summary="Your usage dashboard — account, quota, 30d history, billing",
    description=(
        "Single-shot aggregation for the customer-facing dashboard. "
        "Scoped to the authenticated API key: nothing about other keys or "
        "platform-wide traffic is exposed. Safe to poll."
    ),
)
async def my_dashboard(db: Db, redis: RedisClient, api_key: AuthenticatedKey):
    now = datetime.now(timezone.utc)
    period = api_key.billing_period or "daily"
    limit = int(api_key.daily_limit or 0)

    used = await current_usage(redis, api_key.key_hash, period)  # type: ignore[arg-type]
    remaining = max(0, limit - used)
    percent_used = (used / limit * 100.0) if limit else 0.0

    history = await _read_daily_history(redis, api_key.key_hash, days=30)
    total_30d = sum(r["count"] for r in history)
    days_active = sum(1 for r in history if r["count"] > 0)
    daily_avg = (total_30d / 30.0) if total_30d else 0.0
    peak = max(history, key=lambda r: r["count"]) if history else None
    peak_day = peak if peak and peak["count"] > 0 else None

    # ── Billing snapshot ────────────────────────────────────────────
    billing: dict = {"plan": api_key.tier}
    payg_billable_mtd = 0

    if api_key.tier == "payg":
        month_tag = now.strftime("%Y-%m")
        raw = await redis.get(f"payg_billable:{api_key.key_hash}:{month_tag}")
        payg_billable_mtd = int(raw) if raw else 0
        # settings.payg_price_cents is cents-per-call (0.8 = $0.008)
        estimated_cost_usd = round(
            payg_billable_mtd * (settings.payg_price_cents / 100.0), 4
        )
        billing.update(
            {
                "payg_free_daily_calls": settings.payg_free_daily_calls,
                "payg_billable_mtd": payg_billable_mtd,
                "payg_price_per_call_usd": settings.payg_price_cents / 100.0,
                "payg_estimated_cost_usd": estimated_cost_usd,
            }
        )
    elif api_key.tier == "pro":
        billing.update(
            {"pro_monthly_included": settings.pro_monthly_limit}
        )
    elif api_key.tier == "free":
        billing.update({"free_daily_calls": settings.free_daily_limit})

    # ── Status flag ────────────────────────────────────────────────
    if limit and used >= limit:
        health = "over_limit"
    elif percent_used >= NEAR_LIMIT_PCT:
        health = "near_limit"
    else:
        health = "ok"

    return {
        "generated_at": now.isoformat(),
        "account": {
            "key_prefix": api_key.key_prefix,
            "tier": api_key.tier,
            "billing_period": period,
            "is_active": bool(api_key.is_active),
            "data_pool": api_key.data_pool,
            "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
            "last_used_at": (
                api_key.last_used_at.isoformat() if api_key.last_used_at else None
            ),
        },
        "current_period": {
            "label": "Month-to-date" if period == "monthly" else "Today",
            "period": period,
            "limit": limit,
            "used": used,
            "remaining": remaining,
            "percent_used": round(percent_used, 2),
            "resets_at": _start_of_next_period(now, period).isoformat(),
        },
        "usage_last_30d": history,
        "usage_totals": {
            "total_30d": total_30d,
            "days_active_30d": days_active,
            "daily_avg": round(daily_avg, 2),
            "peak_day": peak_day,
        },
        "billing": billing,
        "status": {
            "health": health,
            "near_limit_threshold_pct": NEAR_LIMIT_PCT,
        },
        "upgrade": _upgrade_hint(api_key.tier, percent_used, payg_billable_mtd),
    }
