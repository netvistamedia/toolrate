from fastapi import APIRouter, Query

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
    category: str | None = Query(None, description="Filter by category (e.g. 'email', 'llm', 'search')"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
):
    gems = await get_hidden_gems(db, category=category, limit=limit)
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
    chains = await get_fallback_chains(db, tool_identifier=tool_identifier, limit=limit)
    return {"tool": tool_identifier, "fallback_chain": chains, "count": len(chains)}
