from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from shared.schemas.recommendations_response import RecommendationsResponse
from shared.schemas.recommendations_request import RecommendationsRequest
from shared.logging.logger import setup_logger, CorrelationIdMiddleware, setup_prometheus, get_correlation_id
from services.recommendation.app.modules.task import recommendation_task

# 로깅 설정
logger = setup_logger("recommendation")
app = FastAPI(title="Recommendation", description="Recommendation for Damo AI Features", version="0.1.0")
app.add_middleware(CorrelationIdMiddleware)
setup_prometheus(app)

# 공통 로직
def _validate_request(request: RecommendationsRequest):
    if not request.user_ids:
        raise HTTPException(status_code=400, detail="userIds is empty")

# 엔드포인트 설정
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "recommendation"}

# 메인 엔드포인트
@app.post("/analyze_refresh", response_model=RecommendationsResponse)
@app.post("/recommendations", response_model=RecommendationsResponse)
async def recommendation_or_refresh(request: Request, body: RecommendationsRequest, background_tasks: BackgroundTasks):
    _validate_request(body)

    log_type = "recommend" if request.url.path == "/recommendations" else "refresh"
    correlation_id = get_correlation_id()
    background_tasks.add_task(recommendation_task, body, correlation_id, log_type)

    return RecommendationsResponse(
        recommendationCount=0,
        recommendedItems=[]
    )
