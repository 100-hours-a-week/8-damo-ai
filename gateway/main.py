import os, httpx
from fastapi import FastAPI, Request, HTTPException
from shared.logging.logger import setup_logger, CorrelationIdMiddleware, setup_prometheus, get_correlation_id
from shared.schemas.update_persona_db_request import UpdatePersonaDBRequest
from shared.schemas.update_persona_db_response import UpdatePersonaDBResponse
from shared.schemas.restaurant_fix_request import RestaurantFixRequest
from shared.schemas.restaurant_fix_response import RestaurantFixResponse
from shared.schemas.recommendations_request import RecommendationsRequest
from shared.schemas.recommendations_response import RecommendationsResponse
from shared.utils.client import ServiceClient

# 로깅 설정
logger = setup_logger("gateway")
app = FastAPI(title="API Gateway", description="API Gateway for Damo AI Features", version="0.1.0")
app.add_middleware(CorrelationIdMiddleware)
setup_prometheus(app)

SERVICE_MAP = {
    "reco": os.getenv("RECOMMENDATION_URL", "http://recommendation:8000"),
    "core": os.getenv("CORE_SERVICE_URL", "http://core_service:8000"),
}

clients = {name: ServiceClient(url) for name, url in SERVICE_MAP.items()}

# 엔드포인트 설정
@app.get("/")
async def root():
    return {"message": "Welcome to the API Gateway"}

@app.get("/ai/api/health")
async def health_check():
    return {"status": "healthy", "service": "gateway"}

# 비즈니스 로직 엔드포인트
async def _proxy_to_logic_container(service_name: str, target_path: str, data: object, response_class):
    target_client = clients[service_name]
    try:
        # data가 Pydantic 모델일 경우 처리
        if hasattr(data, "model_dump"):
            # mode="json" 설정을 하면 datetime, UUID 등이 자동으로 문자열이 됩니다.
            payload = data.model_dump(mode="json")
        else:
            payload = data
            
        logger.info(f"Proxying request to {target_path}")
        result_json = await target_client.post(target_path, json=payload)
        return response_class(**result_json)
    except Exception as e:
        logger.error(f"Proxy error to {target_path}: {str(e)}")
        raise HTTPException(status_code=502, detail="Upstream Service Error")

# Core-Service 공개(Public) 엔드포인트들
@app.post("/ai/api/update_persona_db", response_model=UpdatePersonaDBResponse, tags=["Persona"])
async def update_persona_db(data: UpdatePersonaDBRequest):
    return await _proxy_to_logic_container("core", "/persona", data, UpdatePersonaDBResponse)

@app.post("/ai/api/restaurant_fix", response_model=RestaurantFixResponse, tags=["Recommendation"])
async def restaurant_fix(data: RestaurantFixRequest):
    return await _proxy_to_logic_container("core", "/restaurant_fix", data, RestaurantFixResponse)

@app.post("/ai/api/validate_receipt", tags=["Receipt"])
async def validate_receipt(request: Request):
    body = await request.json()
    return await _proxy_to_logic_container("core", "/validate_receipt", body, dict)

# Recommendation 공개(Public) 엔드포인트들
@app.post("/ai/api/recommendations", response_model=RecommendationsResponse, tags=["Recommendation"])
@app.post("/ai/api/analyze_refresh", response_model=RecommendationsResponse, tags=["Recommendation"])
async def recommendation_handler(request: Request, data: RecommendationsRequest):
    path = request.url.path
    
    # match case를 이용한 타겟 경로 결정
    match path:
        case "/ai/api/recommendations":
            target_path = "/recommendations"
        case "/ai/api/analyze_refresh":
            target_path = "/analyze_refresh"
        case _:
            raise HTTPException(status_code=404)
    return await _proxy_to_logic_container("reco", target_path, data, RecommendationsResponse)