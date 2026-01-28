from fastapi import APIRouter
from src.recommendation.router.routes_v1 import router as recommendation_routes_v1
from src.recommendation.router.routes_v2 import router as recommendation_routes_v2

router = APIRouter()

router.include_router(recommendation_routes_v1, prefix="/v1", tags=["v1"])
router.include_router(recommendation_routes_v2, prefix="/v2", tags=["v2"])
