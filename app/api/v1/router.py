from fastapi import APIRouter

from app.api.v1.assess import router as assess_router
from app.api.v1.report import router as report_router

router = APIRouter(prefix="/v1")
router.include_router(assess_router)
router.include_router(report_router)
