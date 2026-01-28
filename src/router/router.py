from fastapi import APIRouter
from src.router.v1.router import router as v1_router
from src.router.v2.router import router as v2_router

router = APIRouter()

router.include_router(recommendation_routes_v1, prefix="/v1", tags=["v1"])
router.include_router(recommendation_routes_v2, prefix="/v2", tags=["v2"])
