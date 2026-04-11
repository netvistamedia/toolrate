"""CLI for NemoFlow administration.

Usage:
    python -m app.cli create-key --tier free
    python -m app.cli create-key --tier pro --daily-limit 10000
    python -m app.cli create-key --tier enterprise --daily-limit 100000 --data-pool my-company
"""

import argparse
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import generate_api_key
from app.db.session import async_session
from app.models.api_key import ApiKey


async def create_key(tier: str, daily_limit: int | None, data_pool: str | None):
    full_key, key_hash, key_prefix = generate_api_key()

    if daily_limit is None:
        daily_limit = {
            "free": settings.free_daily_limit,
            "pro": settings.pro_daily_limit,
            "enterprise": settings.enterprise_daily_limit,
        }.get(tier, settings.free_daily_limit)

    async with async_session() as db:
        api_key = ApiKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            tier=tier,
            daily_limit=daily_limit,
            data_pool=data_pool,
        )
        db.add(api_key)
        await db.commit()

    print(f"API Key created successfully!")
    print(f"  Key:         {full_key}")
    print(f"  Prefix:      {key_prefix}")
    print(f"  Tier:        {tier}")
    print(f"  Daily limit: {daily_limit}")
    if data_pool:
        print(f"  Data pool:   {data_pool}")
    print()
    print("Save this key now — it cannot be retrieved later.")


def main():
    parser = argparse.ArgumentParser(description="NemoFlow CLI")
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser("create-key", help="Create a new API key")
    create_parser.add_argument("--tier", choices=["free", "pro", "enterprise"], default="free")
    create_parser.add_argument("--daily-limit", type=int, default=None)
    create_parser.add_argument("--data-pool", type=str, default=None)

    args = parser.parse_args()

    if args.command == "create-key":
        asyncio.run(create_key(args.tier, args.daily_limit, args.data_pool))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
