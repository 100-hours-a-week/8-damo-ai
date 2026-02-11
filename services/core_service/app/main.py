from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from shared.logging.logger import setup_logger, CorrelationIdMiddleware, setup_prometheus, get_correlation_id
from shared.schemas.update_persona_db_request import UpdatePersonaDBRequest
from shared.schemas.update_persona_db_response import UpdatePersonaDBResponse
from shared.schemas.restaurant_fix_request import RestaurantFixRequest
from shared.schemas.restaurant_fix_response import RestaurantFixResponse
from services.core_service.app.modules.bucket import bucket_manager
from services.core_service.app.modules.persona.graph import persona_graph
import time

# 로깅 설정
logger = setup_logger("core_service")
app = FastAPI(title="Core Service", description="Core Service for Damo AI Features", version="0.1.0")
app.add_middleware(CorrelationIdMiddleware)
setup_prometheus(app)

# 엔드포인트 설정
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "core_service"}

async def _analyze_persona_task(body: UpdatePersonaDBRequest, correlation_id: str):
    """백그라운드에서 수행될 페르소나 분석 및 DB 업로드 로직"""
    logger.info(f"Starting background persona analysis for user: {body.user_data.id} [CID: {correlation_id}]")
    try:
        # LangGraph 실행
        # TODO: 실제 DB를 조회하여 최초 생성 여부(is_first_time) 판단 로직 추가 필요
        initial_state = {
            "request_body": body,
            "is_first_time": True, 
            "retry_count": 0
        }
        
        await persona_graph.ainvoke(initial_state)
        
        logger.info(f"Background analysis completed successfully for user: {body.user_data.id}")
    except Exception as e:
        logger.error(f"Error in background persona analysis for user {body.user_data.id}: {str(e)}")

@app.post("/persona", response_model=UpdatePersonaDBResponse)
async def update_persona_db(body: UpdatePersonaDBRequest, background_tasks: BackgroundTasks):
    """
    사용자 데이터를 받아서 유효성 검사 후 즉시 응답하고,
    무거운 분석 작업은 백그라운드로 넘깁니다.
    """
    if not body.user_data:
        raise HTTPException(status_code=422, detail="User data is missing")

    # 백그라운드 작업 등록
    correlation_id = get_correlation_id()
    background_tasks.add_task(_analyze_persona_task, body, correlation_id)

    return UpdatePersonaDBResponse(
        success=True,
        user_id=body.user_data.id
    )

@app.post("/restaurant_fix", response_model=RestaurantFixResponse)
async def restaurant_fix(body: RestaurantFixRequest, request: Request):
    logger.info(f"Received restaurant_fix for restaurant_id: {body.restaurant_id}")
    return RestaurantFixResponse(
        success=True,
        restaurant_id=body.restaurant_id
    )

# @app.post("/validate_receipt")
# async def validate_receipt(request: Request):
#     print(await request.json())
#     request_id=request.headers.get("X-Request-ID")
#     print(request_id)
#     return {"status": "healthy", "service": "core_service"}