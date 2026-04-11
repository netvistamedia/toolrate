"""
Partition manager for execution_reports table.

Creates monthly partitions ahead of time and drops old ones beyond retention.
Run via: docker compose exec app python scripts/manage-partitions.py

Designed to run as a monthly cron or on each deploy.
"""
import asyncio
import argparse
from datetime import datetime, timedelta

import asyncpg


PARTITION_TABLE = "execution_reports"
PARTITION_COLUMN = "created_at"
MONTHS_AHEAD = 3       # Always have 3 months of future partitions ready
MONTHS_RETAIN = 12     # Keep 12 months of historical data


async def ensure_partitions(conn: asyncpg.Connection, months_ahead: int, months_retain: int, dry_run: bool = False):
    """Create missing future partitions and drop expired ones."""

    now = datetime.utcnow()

    # --- Create future partitions ---
    for offset in range(-1, months_ahead + 1):
        year = now.year + (now.month + offset - 1) // 12
        month = (now.month + offset - 1) % 12 + 1
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)

        partition_name = f"{PARTITION_TABLE}_y{start.year}m{start.month:02d}"
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_class WHERE relname = $1", partition_name
        )
        if exists:
            continue

        sql = (
            f'CREATE TABLE IF NOT EXISTS "{partition_name}" '
            f'PARTITION OF "{PARTITION_TABLE}" '
            f"FOR VALUES FROM ('{start.isoformat()}') TO ('{end.isoformat()}')"
        )
        print(f"  CREATE partition {partition_name} [{start.date()} .. {end.date()})")
        if not dry_run:
            await conn.execute(sql)

    # --- Drop old partitions beyond retention ---
    cutoff = datetime(now.year, now.month, 1) - timedelta(days=months_retain * 31)
    rows = await conn.fetch(
        """
        SELECT inhrelid::regclass::text AS partition_name
        FROM pg_inherits
        WHERE inhparent = $1::regclass
        ORDER BY inhrelid::regclass::text
        """,
        PARTITION_TABLE,
    )
    for row in rows:
        name = row["partition_name"]
        # Parse y2026m04 from name
        try:
            parts = name.split("_y")[1]
            y, m = parts.split("m")
            partition_date = datetime(int(y), int(m), 1)
        except (IndexError, ValueError):
            continue

        if partition_date < cutoff:
            print(f"  DROP partition {name} (older than {months_retain} months)")
            if not dry_run:
                await conn.execute(f'DROP TABLE "{name}"')


async def main():
    parser = argparse.ArgumentParser(description="Manage execution_reports partitions")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    parser.add_argument("--database-url", default="postgresql://nemo:nemo@postgres:5432/nemoflow")
    args = parser.parse_args()

    print(f"Partition manager for {PARTITION_TABLE}")
    print(f"  Months ahead: {MONTHS_AHEAD}, Retention: {MONTHS_RETAIN} months")
    if args.dry_run:
        print("  DRY RUN — no changes will be made")

    conn = await asyncpg.connect(args.database_url)
    try:
        await ensure_partitions(conn, MONTHS_AHEAD, MONTHS_RETAIN, dry_run=args.dry_run)
    finally:
        await conn.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
