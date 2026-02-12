from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from shared.logging.logger import setup_logger, CorrelationIdMiddleware, setup_prometheus, get_correlation_id
from shared.schemas.update_persona_db_request import UpdatePersonaDBRequest
from shared.schemas.update_persona_db_response import UpdatePersonaDBResponse
from shared.schemas.restaurant_fix_request import RestaurantFixRequest
from shared.schemas.restaurant_fix_response import RestaurantFixResponse
from services.core_service.app.modules.persona.task import analyze_persona_task
from services.core_service.app.modules.fix.task import fix_task

# 로깅 설정
logger = setup_logger("core_service")
app = FastAPI(title="Core Service", description="Core Service for Damo AI Features", version="0.1.0")
app.add_middleware(CorrelationIdMiddleware)
setup_prometheus(app)

# 엔드포인트 설정
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "core_service"}

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
    background_tasks.add_task(analyze_persona_task, body, correlation_id)

    return UpdatePersonaDBResponse(
        success=True,
        user_id=body.user_data.id
    )

@app.post("/restaurant_fix", response_model=RestaurantFixResponse)
async def restaurant_fix(body: RestaurantFixRequest):
    if not body.restaurant_id:
        raise HTTPException(status_code=422, detail="restaurant_id is missing")

    return await fix_task(body)

# @app.post("/validate_receipt")
# async def validate_receipt(request: Request):
#     print(await request.json())
#     request_id=request.headers.get("X-Request-ID")
#     print(request_id)
#     return {"status": "healthy", "service": "core_service"}