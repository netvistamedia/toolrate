from fastapi import APIRouter, Query

from app.core.categories import normalize_category
from app.core.identifiers import normalize_identifier
from app.dependencies import Db, AuthenticatedKey
from app.services.discovery import get_hidden_gems, get_fallback_chains

router = APIRouter()


@router.get("/discover/hidden-gems", tags=["Discovery"],
            summary="Find hidden gem tools",
            description="Discover tools that are rarely the first choice but have high success rates as fallbacks. "
                        "Based on real agent journey data — what agents switch to after their first choice fails.")
async def hidden_gems(
    db: Db,
    api_key: AuthenticatedKey,
    category: str | None = Query(None, description="Filter by category (e.g. 'LLM APIs', 'Search APIs'). Short aliases are normalized to the canonical name."),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
):
    # Normalize so old clients (?category=llm) hit the same canonical name
    # the DB stores post-2026-04-14 merge.
    normalized_cat = normalize_category(category) if category else None
    gems = await get_hidden_gems(db, category=normalized_cat, limit=limit)
    return {"hidden_gems": gems, "count": len(gems)}


@router.get("/discover/fallback-chain", tags=["Discovery"],
            summary="Get fallback chain for a tool",
            description="When this tool fails, what do agents typically switch to? "
                        "Shows the most successful fallback tools based on real agent behavior.")
async def fallback_chain(
    db: Db,
    api_key: AuthenticatedKey,
    tool_identifier: str = Query(..., description="The tool to find fallbacks for"),
    limit: int = Query(5, ge=1, le=20, description="Max results"),
):
    # ``previous_tool`` is normalized at write time (report_ingest), so the
    # lookup must normalize too — otherwise the canonical row never matches
    # for callers querying with mixed-case URLs or trailing slashes.
    canonical = normalize_identifier(tool_identifier)
    chains = await get_fallback_chains(db, tool_identifier=canonical, limit=limit)
    return {"tool": canonical, "fallback_chain": chains, "count": len(chains)}
