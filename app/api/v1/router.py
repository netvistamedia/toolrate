from fastapi import APIRouter

from app.api.v1.assess import router as assess_router
from app.api.v1.auth import router as auth_router
from app.api.v1.discover import router as discover_router
from app.api.v1.report import router as report_router
from app.api.v1.stats import router as stats_router
from app.api.v1.tools import router as tools_router
from app.api.v1.webhooks import router as webhooks_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router)
router.include_router(assess_router)
router.include_router(report_router)
router.include_router(discover_router)
router.include_router(stats_router)
router.include_router(tools_router)
router.include_router(webhooks_router)
