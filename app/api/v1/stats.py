from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from sqlalchemy import select, func, and_

from app.dependencies import Db, RedisClient, AuthenticatedKey
from app.models.tool import Tool
from app.models.report import ExecutionReport
from app.models.api_key import ApiKey

router = APIRouter()


@router.get("/stats", tags=["Stats"],
            summary="Platform statistics",
            description="Get NemoFlow platform stats: total tools, reports, API keys, and daily activity.")
async def platform_stats(
    db: Db,
    redis: RedisClient,
    api_key: AuthenticatedKey,
):
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)

    # Total tools
    tools_result = await db.execute(select(func.count()).select_from(Tool))
    total_tools = tools_result.scalar()

    # Total reports
    reports_result = await db.execute(select(func.count()).select_from(ExecutionReport))
    total_reports = reports_result.scalar()

    # Reports today
    reports_today_result = await db.execute(
        select(func.count()).select_from(ExecutionReport)
        .where(ExecutionReport.created_at >= today)
    )
    reports_today = reports_today_result.scalar()

    # Reports last 7 days
    reports_7d_result = await db.execute(
        select(func.count()).select_from(ExecutionReport)
        .where(ExecutionReport.created_at >= last_7d)
    )
    reports_7d = reports_7d_result.scalar()

    # Total API keys
    keys_result = await db.execute(
        select(func.count()).select_from(ApiKey).where(ApiKey.is_active == True)  # noqa: E712
    )
    total_keys = keys_result.scalar()

    # Reports with journey data
    journey_result = await db.execute(
        select(func.count()).select_from(ExecutionReport)
        .where(ExecutionReport.session_id.isnot(None))
    )
    journey_reports = journey_result.scalar()

    # Top 10 most assessed tools (by report count)
    top_tools_result = await db.execute(
        select(Tool.identifier, Tool.display_name, Tool.report_count)
        .order_by(Tool.report_count.desc())
        .limit(10)
    )
    top_tools = [
        {"identifier": r.identifier, "display_name": r.display_name, "report_count": r.report_count}
        for r in top_tools_result.all()
    ]

    return {
        "platform": {
            "total_tools": total_tools,
            "total_reports": total_reports,
            "total_api_keys": total_keys,
            "journey_reports": journey_reports,
        },
        "activity": {
            "reports_today": reports_today,
            "reports_last_7d": reports_7d,
        },
        "top_tools": top_tools,
        "generated_at": now.isoformat(),
    }


@router.get("/stats/me", tags=["Stats"],
            summary="Your usage statistics",
            description="Get your personal API key usage stats.")
async def my_stats(
    db: Db,
    redis: RedisClient,
    api_key: AuthenticatedKey,
):
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Get current daily usage from Redis
    from datetime import date
    date_key = f"rl:{api_key.key_hash}:{date.today().isoformat()}"
    daily_used = await redis.get(date_key)

    return {
        "key_prefix": api_key.key_prefix,
        "tier": api_key.tier,
        "daily_limit": api_key.daily_limit,
        "daily_used": int(daily_used) if daily_used else 0,
        "daily_remaining": api_key.daily_limit - (int(daily_used) if daily_used else 0),
        "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
    }
