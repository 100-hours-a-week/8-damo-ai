from fastapi import FastAPI, APIRouter
import uvicorn

app = FastAPI(title="Damo AI Pipeline API", version="0.0.1")


@app.get("/")
async def root():
    """루트 엔드포인트 - 간단한 환영 메시지"""
    return {
        "message": "Welcome to Damo AI Pipeline API",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "ok",
        "message": "Server is healthy"
    }


# -------------------------
# v1 API
# -------------------------
from src.features.recommendation.api import routes_v1 as recommendation_routes_v1

v1_router = APIRouter(prefix="/ai/api/v1")
v1_router.include_router(recommendation_routes_v1.router, tags=["v1"])
app.include_router(v1_router)


# -------------------------
# v2 API
# -------------------------
from src.features.ocr.api import routes as ocr_routes
from src.features.recommendation.api import routes_v2 as recommendation_routes_v2

v2_router = APIRouter(prefix="/ai/api/v2")
v2_router.include_router(ocr_routes.router, tags=["v2"])
v2_router.include_router(recommendation_routes_v2.router, tags=["v2"])
app.include_router(v2_router)


if __name__ == "__main__":
    # 개발용 서버 실행
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
