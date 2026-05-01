"""CLI for ToolRate administration.

Usage:
    python -m app.cli create-key --tier free
    python -m app.cli create-key --tier payg
    python -m app.cli create-key --tier pro
    python -m app.cli create-key --tier enterprise --limit 1000000 --data-pool ent:acme
    python -m app.cli stats
"""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.config import settings
from app.core.security import generate_api_key
from app.db.session import async_session
from app.models.api_key import ApiKey
from app.models.report import ExecutionReport


TIER_DEFAULTS = {
    "free":       ("daily",   "free_daily_limit"),
    "payg":       ("daily",   "payg_daily_hard_cap"),
    "pro":        ("monthly", "pro_monthly_limit"),
    "enterprise": ("daily",   "enterprise_daily_limit"),
    "admin":      ("daily",   "enterprise_daily_limit"),
}


async def create_key(tier: str, limit: int | None, data_pool: str | None):
    full_key, key_hash, key_prefix = generate_api_key()

    period, default_attr = TIER_DEFAULTS[tier]
    if limit is None:
        limit = getattr(settings, default_attr)

    async with async_session() as db:
        api_key = ApiKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            tier=tier,
            daily_limit=limit,
            billing_period=period,
            data_pool=data_pool,
        )
        db.add(api_key)
        await db.commit()

    print("API Key created successfully!")
    print(f"  Key:          {full_key}")
    print(f"  Prefix:       {key_prefix}")
    print(f"  Tier:         {tier}")
    print(f"  Period:       {period}")
    print(f"  Limit:        {limit} / {'day' if period == 'daily' else 'month'}")
    if data_pool:
        print(f"  Data pool:    {data_pool}")
    print()
    print("Save this key now — it cannot be retrieved later.")


async def show_stats():
    now = datetime.now(timezone.utc)
    d7 = now - timedelta(days=7)
    d1 = now - timedelta(days=1)

    async with async_session() as db:
        async def count(stmt):
            return (await db.execute(stmt)).scalar() or 0

        total_keys     = await count(select(func.count()).select_from(ApiKey))
        active_keys    = await count(select(func.count()).select_from(ApiKey).where(ApiKey.is_active.is_(True)))
        keys_used      = await count(select(func.count()).select_from(ApiKey).where(ApiKey.last_used_at.is_not(None)))
        keys_used_7d   = await count(select(func.count()).select_from(ApiKey).where(ApiKey.last_used_at >= d7))
        keys_used_1d   = await count(select(func.count()).select_from(ApiKey).where(ApiKey.last_used_at >= d1))
        new_keys_7d    = await count(select(func.count()).select_from(ApiKey).where(ApiKey.created_at >= d7))

        total_reports  = await count(select(func.count()).select_from(ExecutionReport))
        reports_7d     = await count(select(func.count()).select_from(ExecutionReport).where(ExecutionReport.created_at >= d7))
        reports_1d     = await count(select(func.count()).select_from(ExecutionReport).where(ExecutionReport.created_at >= d1))

        tier_rows   = (await db.execute(select(ApiKey.tier, func.count()).group_by(ApiKey.tier))).all()
        source_rows = (await db.execute(select(ApiKey.source, func.count()).group_by(ApiKey.source))).all()

    print("=== API keys ===")
    print(f"  Total:          {total_keys}")
    print(f"  Active:         {active_keys}")
    print(f"  Ever used:      {keys_used}")
    print(f"  Used last 7d:   {keys_used_7d}")
    print(f"  Used last 24h:  {keys_used_1d}")
    print(f"  New last 7d:    {new_keys_7d}")
    print()
    print("  By tier:")
    for tier, count_ in sorted(tier_rows):
        print(f"    {tier:<10} {count_}")
    print()
    print("  By source:")
    for source, count_ in sorted(source_rows, key=lambda x: -x[1]):
        print(f"    {(source or '(null)'):<10} {count_}")
    print()
    print("=== Execution reports ===")
    print(f"  Total:          {total_reports}")
    print(f"  Last 7d:        {reports_7d}")
    print(f"  Last 24h:       {reports_1d}")


def main():
    parser = argparse.ArgumentParser(description="ToolRate CLI")
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser("create-key", help="Create a new API key")
    create_parser.add_argument("--tier", choices=list(TIER_DEFAULTS.keys()), default="free")
    create_parser.add_argument("--limit", type=int, default=None,
                               help="Hard limit for the period (daily for free/payg/enterprise, monthly for pro)")
    create_parser.add_argument("--data-pool", type=str, default=None)

    subparsers.add_parser("stats", help="Show aggregate usage stats (no PII)")

    args = parser.parse_args()

    if args.command == "create-key":
        asyncio.run(create_key(args.tier, args.limit, args.data_pool))
    elif args.command == "stats":
        asyncio.run(show_stats())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
