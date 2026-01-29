from fastapi import APIRouter
from src.ocr.api import routes as ocr_routes
from src.recommendation.router import routes_v2 as recommendation_routes

router = APIRouter()

router.include_router(ocr_routes.router, tags=["v2"])
router.include_router(recommendation_routes.router, tags=["v2"])
