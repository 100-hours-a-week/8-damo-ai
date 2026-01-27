from fastapi import APIRouter
from src.recommendation.api import routes_v1 as recommendation_routes

router = APIRouter()

router.include_router(recommendation_routes.router, tags=["v1"])
