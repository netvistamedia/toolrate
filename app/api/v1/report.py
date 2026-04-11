from fastapi import APIRouter, Request

from app.dependencies import Db, RedisClient, AuthenticatedKey
from app.core.security import make_fingerprint
from app.schemas.report import ReportRequest, ReportResponse
from app.services.report_ingest import ingest_report

router = APIRouter()


@router.post("/report", response_model=ReportResponse)
async def submit_report(
    body: ReportRequest,
    request: Request,
    db: Db,
    redis: RedisClient,
    api_key: AuthenticatedKey,
):
    client_ip = request.client.host if request.client else "unknown"
    fingerprint = make_fingerprint(api_key.key_hash, client_ip)

    tool, report = await ingest_report(
        db=db,
        redis=redis,
        tool_identifier=body.tool_identifier,
        success=body.success,
        error_category=body.error_category,
        latency_ms=body.latency_ms,
        context=body.context,
        reporter_fingerprint=fingerprint,
        data_pool=api_key.data_pool,
    )

    return ReportResponse(tool_id=str(tool.id))
