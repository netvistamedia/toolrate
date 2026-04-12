from fastapi import APIRouter, Query
from sqlalchemy import select, func

from app.dependencies import Db, AuthenticatedKey
from app.models.tool import Tool

router = APIRouter()


@router.get("/tools", tags=["Discovery"],
            summary="Search and browse tools",
            description="Browse all rated tools with optional filtering by category and search by name or identifier. "
                        "Results are paginated and sorted by report count (most data first).")
async def list_tools(
    db: Db,
    api_key: AuthenticatedKey,
    q: str | None = Query(None, max_length=256, description="Search by name or identifier (case-insensitive substring match)"),
    category: str | None = Query(None, max_length=128, description="Filter by category (e.g. 'email', 'llm', 'payment')"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Results per page"),
):
    stmt = select(Tool)

    if q:
        # Escape SQL wildcards in user input to prevent pattern injection
        escaped = q.replace("%", r"\%").replace("_", r"\_")
        pattern = f"%{escaped}%"
        stmt = stmt.where(
            Tool.identifier.ilike(pattern, escape="\\") | Tool.display_name.ilike(pattern, escape="\\")
        )

    if category:
        stmt = stmt.where(Tool.category == category)

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()

    # Get page
    stmt = stmt.order_by(Tool.report_count.desc()).offset(offset).limit(limit)
    results = (await db.execute(stmt)).scalars().all()

    return {
        "tools": [
            {
                "identifier": t.identifier,
                "display_name": t.display_name,
                "category": t.category,
                "report_count": t.report_count,
                "first_seen_at": t.first_seen_at.isoformat() if t.first_seen_at else None,
            }
            for t in results
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/tools/categories", tags=["Discovery"],
            summary="List all tool categories",
            description="Returns all available tool categories with the number of tools in each.")
async def list_categories(
    db: Db,
    api_key: AuthenticatedKey,
):
    stmt = (
        select(Tool.category, func.count(Tool.id).label("count"))
        .where(Tool.category.is_not(None))
        .group_by(Tool.category)
        .order_by(func.count(Tool.id).desc())
    )
    rows = (await db.execute(stmt)).all()
    return {
        "categories": [{"name": row[0], "tool_count": row[1]} for row in rows],
        "total": len(rows),
    }
