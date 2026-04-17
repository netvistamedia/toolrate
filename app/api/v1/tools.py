from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import case, func, select

from app.core.categories import normalize_category
from app.core.identifiers import normalize_identifier
from app.core.security import context_hash as _context_hash, effective_data_pool
from app.dependencies import Db, RedisClient, AuthenticatedKey
from app.models.report import ExecutionReport
from app.models.tool import Tool
from app.services.cache import get_cached_score, set_cached_score
from app.services.scoring import compute_score

router = APIRouter()


@router.get("/tools", tags=["Discovery"],
            summary="Search and browse tools",
            description="Browse all rated tools with optional filtering by category and search by name or identifier. "
                        "Results are paginated and sorted by report count (most data first).")
async def list_tools(
    db: Db,
    api_key: AuthenticatedKey,
    q: str | None = Query(None, max_length=256, description="Search by name or identifier (case-insensitive substring match)"),
    category: str | None = Query(None, max_length=128, description="Filter by category (e.g. 'LLM APIs', 'Payment APIs', 'Email APIs'). Short aliases like 'llm' or 'payment' are normalized to the canonical name."),
    offset: int = Query(0, ge=0, le=10000, description="Pagination offset"),
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
        # Accept old lowercase aliases (?category=llm) and route them to the
        # canonical Title-Case name the DB actually stores. Without this, the
        # 2026-04-14 category merge silently broke every existing client that
        # was filtering by the pre-merge spelling.
        stmt = stmt.where(Tool.category == (normalize_category(category) or category))

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


@router.get("/tools/{identifier:path}", tags=["Discovery"],
            summary="Get tool detail",
            description="Returns full metadata and the current reliability assessment for a single tool. "
                        "The identifier should be URL-encoded when it contains slashes (e.g. a full API URL). "
                        "Responds with 404 if the tool is unknown.")
async def get_tool_detail(
    identifier: str,
    db: Db,
    redis: RedisClient,
    api_key: AuthenticatedKey,
):
    # Canonicalise so `/v1/tools/HTTPS:%2F%2FAPI.Stripe.Com%2F` hits the same
    # DB row as `/v1/tools/https:%2F%2Fapi.stripe.com`. Rows are stored under
    # the normalized identifier, so a raw lookup 404s on any case/slash
    # variant of a tool that actually exists.
    canonical = normalize_identifier(identifier)
    result = await db.execute(select(Tool).where(Tool.identifier == canonical))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {canonical}",
        )

    ctx_hash = _context_hash("")
    data_pool = effective_data_pool(api_key.data_pool)

    cached = await get_cached_score(redis, str(tool.id), ctx_hash, data_pool)
    if cached:
        assessment = cached
    else:
        assessment = await compute_score(db, tool, ctx_hash, data_pool)
        from app.config import settings
        ttl = (
            settings.cache_ttl_hot
            if tool.report_count >= settings.hot_threshold_reports_7d
            else settings.cache_ttl_cold
        )
        await set_cached_score(redis, str(tool.id), ctx_hash, data_pool, assessment, ttl)

    now = datetime.now(timezone.utc)
    cutoff_30d = now - timedelta(days=30)
    cutoff_7d = now - timedelta(days=7)
    cutoff_24h = now - timedelta(hours=24)

    counts_stmt = (
        select(
            func.count().label("total"),
            func.sum(case((ExecutionReport.created_at >= cutoff_30d, 1), else_=0)).label("r_30d"),
            func.sum(case((ExecutionReport.created_at >= cutoff_7d, 1), else_=0)).label("r_7d"),
            func.sum(case((ExecutionReport.created_at >= cutoff_24h, 1), else_=0)).label("r_24h"),
        )
        .where(ExecutionReport.tool_id == tool.id)
    )
    row = (await db.execute(counts_stmt)).one()

    return {
        "identifier": tool.identifier,
        "display_name": tool.display_name,
        "category": tool.category,
        "first_seen_at": tool.first_seen_at.isoformat() if tool.first_seen_at else None,
        "report_count": tool.report_count,
        "activity": {
            "reports_total": int(row.total or 0),
            "reports_30d": int(row.r_30d or 0),
            "reports_7d": int(row.r_7d or 0),
            "reports_24h": int(row.r_24h or 0),
        },
        "assessment": assessment,
    }
