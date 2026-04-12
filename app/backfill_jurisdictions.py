"""One-shot backfill: enrich existing tools with jurisdiction metadata.

Runs the hybrid resolver against every Tool in the DB. Behavior:

    * Tools whose current jurisdiction_source is 'manual' are left alone
      unless --force is passed — manual entries are authoritative.
    * All other tools are re-resolved. Seeded tools pick up their manual
      override, WHOIS-eligible tools get company-level data, and the rest
      fall through to IP geolocation (flagged cdn_detected when the edge
      is a CDN).

Usage (inside the app container):
    docker compose exec app python -m app.backfill_jurisdictions
    docker compose exec app python -m app.backfill_jurisdictions --limit 20
    docker compose exec app python -m app.backfill_jurisdictions --force
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import select

from app.db.session import async_session
from app.models.tool import Tool
from app.services.jurisdiction import enrich_tool

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill jurisdiction metadata for existing tools")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max tools to process (for testing)")
    parser.add_argument("--concurrency", type=int, default=6,
                        help="Parallel lookups (WHOIS is slow-ish; default 6)")
    parser.add_argument("--force", action="store_true",
                        help="Re-resolve even tools with manual source set")
    args = parser.parse_args()

    async with async_session() as db:
        stmt = select(Tool)
        if not args.force:
            stmt = stmt.where(
                (Tool.jurisdiction_source.is_(None))
                | (Tool.jurisdiction_source != "manual")
            )
        if args.limit:
            stmt = stmt.limit(args.limit)
        ids = [t.id for t in (await db.execute(stmt)).scalars().all()]

    total = len(ids)
    if total == 0:
        logger.info("No tools to backfill (use --force to re-resolve manual entries).")
        return

    logger.info("Backfilling jurisdiction for %d tools (concurrency=%d, force=%s)",
                total, args.concurrency, args.force)

    semaphore = asyncio.Semaphore(args.concurrency)
    counts = {"manual": 0, "whois": 0, "ip_geolocation": 0, "cdn_detected": 0, "skipped": 0, "failed": 0}

    async with async_session() as db:
        # Load all rows into memory so we can update in a single transaction.
        tools = (await db.execute(select(Tool).where(Tool.id.in_(ids)))).scalars().all()

        async def process(tool: Tool) -> None:
            async with semaphore:
                try:
                    if await enrich_tool(tool):
                        source = tool.jurisdiction_source or "ip_geolocation"
                        counts[source] = counts.get(source, 0) + 1
                    else:
                        counts["skipped"] += 1
                except Exception as exc:
                    counts["failed"] += 1
                    logger.warning("Failed for %s: %s", tool.identifier, exc)

        await asyncio.gather(*(process(t) for t in tools))
        await db.commit()

    logger.info("Backfill complete: %s", ", ".join(f"{k}={v}" for k, v in counts.items()))


if __name__ == "__main__":
    asyncio.run(main())
