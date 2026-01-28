from fastapi import APIRouter
from src.recommendation.router.routes_v1 import router as recommendation_routes

router = APIRouter()

router.include_router(recommendation_routes, tags=["v1"])
