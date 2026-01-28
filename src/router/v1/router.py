from fastapi import APIRouter
from src.recommendation.router import routes_v1 as recommendation_routes

router = APIRouter()

router.include_router(recommendation_routes, tags=["v1"])
