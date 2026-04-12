"""One-shot backfill: enrich existing tools with jurisdiction metadata.

Iterates every tool whose jurisdiction_category is NULL, resolves its
hostname to a country/provider via the jurisdiction service, and writes
the result back. Safe to re-run — already-enriched tools are skipped.

Usage (inside the app container):
    docker compose exec app python -m app.backfill_jurisdictions
    docker compose exec app python -m app.backfill_jurisdictions --limit 50
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
                        help="Max tools to process this run (for testing)")
    parser.add_argument("--concurrency", type=int, default=8,
                        help="Number of parallel lookups (ipinfo.io free tier allows bursts)")
    args = parser.parse_args()

    async with async_session() as db:
        stmt = select(Tool).where(Tool.jurisdiction_category.is_(None))
        if args.limit:
            stmt = stmt.limit(args.limit)
        tools = (await db.execute(stmt)).scalars().all()

    total = len(tools)
    if total == 0:
        logger.info("No tools to backfill.")
        return

    logger.info("Backfilling jurisdiction for %d tools (concurrency=%d)", total, args.concurrency)

    semaphore = asyncio.Semaphore(args.concurrency)
    counts = {"enriched": 0, "skipped": 0, "failed": 0}

    async def process(tool: Tool) -> None:
        async with semaphore:
            try:
                if await enrich_tool(tool):
                    counts["enriched"] += 1
                else:
                    counts["skipped"] += 1
            except Exception as exc:
                counts["failed"] += 1
                logger.warning("Failed for %s: %s", tool.identifier, exc)

    # Detach the tools from the query session — we'll re-attach them in a writable session.
    async with async_session() as db:
        # Reload via fresh session so updates persist
        ids = [t.id for t in tools]
        refreshed = (await db.execute(select(Tool).where(Tool.id.in_(ids)))).scalars().all()
        await asyncio.gather(*(process(t) for t in refreshed))
        await db.commit()

    logger.info(
        "Backfill complete: enriched=%d skipped=%d failed=%d",
        counts["enriched"], counts["skipped"], counts["failed"],
    )


if __name__ == "__main__":
    asyncio.run(main())
