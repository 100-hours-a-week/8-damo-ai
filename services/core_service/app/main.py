from fastapi import FastAPI, Request, HTTPException
from shared.logging.logger import setup_logger, CorrelationIdMiddleware, setup_prometheus, get_correlation_id
from shared.schemas.update_persona_db_request import UpdatePersonaDBRequest
from shared.schemas.update_persona_db_response import UpdatePersonaDBResponse
from shared.schemas.restaurant_fix_request import RestaurantFixRequest
from shared.schemas.restaurant_fix_response import RestaurantFixResponse

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
async def update_persona_db(body: UpdatePersonaDBRequest, request: Request):
    print(body)
    request_id = request.headers.get("X-Request-ID")
    print(f"X-Request-ID: {request_id}")
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