"""CLI for NemoFlow administration.

Usage:
    python -m app.cli create-key --tier free
    python -m app.cli create-key --tier payg
    python -m app.cli create-key --tier pro
    python -m app.cli create-key --tier enterprise --limit 1000000 --data-pool ent:acme
"""

import argparse
import asyncio

from app.config import settings
from app.core.security import generate_api_key
from app.db.session import async_session
from app.models.api_key import ApiKey


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
    print(f"  Limit:        {limit} / {period[:-2]}")
    if data_pool:
        print(f"  Data pool:    {data_pool}")
    print()
    print("Save this key now — it cannot be retrieved later.")


def main():
    parser = argparse.ArgumentParser(description="NemoFlow CLI")
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser("create-key", help="Create a new API key")
    create_parser.add_argument("--tier", choices=list(TIER_DEFAULTS.keys()), default="free")
    create_parser.add_argument("--limit", type=int, default=None,
                               help="Hard limit for the period (daily for free/payg/enterprise, monthly for pro)")
    create_parser.add_argument("--data-pool", type=str, default=None)

    args = parser.parse_args()

    if args.command == "create-key":
        asyncio.run(create_key(args.tier, args.limit, args.data_pool))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
