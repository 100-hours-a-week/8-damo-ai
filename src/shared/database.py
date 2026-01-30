from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from src.core.config import settings
from src.recommendation.schemas.dining_session import DiningSession, RestaurantCandidate
from bson import ObjectId
from typing import Optional, Union
from src.recommendation.schemas.recommendations_request import RecommendationsRequest
from src.recommendation.schemas.recommendations_response import RecommendationsResponse
from src.recommendation.schemas.restaurant_fix_response import RestaurantFixResponse
from src.recommendation.schemas.recommended_item import RecommendedItem
from src.recommendation.data.mock_items import MOCK_DEV_ITEMS
import asyncio

class Database:
    client: AsyncIOMotorClient = None

db_wrapper = Database()

def get_client() -> AsyncIOMotorClient:
    """MongoDB Client 싱글톤 반환 (이벤트 루프 변화 대응)"""
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None
    # 클라이언트가 없거나, 기존 클라이언트의 루프와 현재 루프가 다를 경우 새로 생성
    if db_wrapper.client is None:
        db_wrapper.client = AsyncIOMotorClient(settings.MONGODB_URI)
    elif current_loop and db_wrapper.client.get_io_loop() != current_loop:
        # 기존 클라이언트의 소켓 등을 닫고 새로 생성
        db_wrapper.client.close()
        db_wrapper.client = AsyncIOMotorClient(settings.MONGODB_URI)
        
    return db_wrapper.client

def get_db() -> AsyncIOMotorDatabase:
    """기본 데이터베이스(damo) 반환"""
    client = get_client()
    return client[settings.DB_NAME]

# 샘플 코드
# 백엔드에서 흐름 테스트용도로 사용
# 추후 실제 동작 코드로 교체 예정
def to_recommendations_response(data: Union[DiningSession, dict]) -> RecommendationsResponse:
    """DiningSession 객체 또는 MongoDB dict를 RecommendationsResponse로 변환"""
    session = DiningSession.model_validate(data) if isinstance(data, dict) else data
    
    # 1. 항목 리스트 생성
    items = [
        RecommendedItem(
            restaurant_id=c.restaurant_id,
            score=c.score,
            reasoning_description=c.reasoning
        ) for c in session.restaurant_candidate
    ]
    
    # 2. 스키마에 정의된 정확한 필드명(recommended_items) 사용
    return RecommendationsResponse(
        recommendation_count=session.current_phase,
        recommended_items=items  # restaurant_candidates -> recommended_items로 변경
    )

async def create_dining_session(request: RecommendationsRequest) -> Union[str, None]:
    # 1. Mock 데이터를 DiningSession의 RestaurantCandidate 형식으로 변환
    mock_candidates = [
        RestaurantCandidate(
            restaurant_id=item.restaurant_id,
            score=item.score,
            reasoning=item.reasoning_description  # reasoning_description -> reasoning 매핑
        ) for item in MOCK_DEV_ITEMS
    ]

    session = DiningSession(
        dining_id=request.dining_data.dining_id,
        groups_id=request.dining_data.groups_id, # 요청 스키마에 따라 조정 필요
        dining_date=request.dining_data.dining_date,
        budget=request.dining_data.budget,
        x=str(request.dining_data.x),
        y=str(request.dining_data.y),
        current_phase=1,
        is_completed=False,
        phases=[], # 초기 Phase 데이터
        restaurant_candidate=mock_candidates,
        final_restaurant=[]
    )

    db = get_db()
    collection = db["dining_sessions"]
    
    # 0. 이미 완료된 세션인지 체크
    existing = await collection.find_one({"diningId": request.dining_data.dining_id})
    if existing and existing.get("isCompleted"):
        return None  # 또는 특정 에러 처리를 위한 값

    session_data = session.model_dump(by_alias=True, exclude_none=True)
    
    # 1. _id 필드 제거 (upsert 시 MongoDB가 기존 ID를 유지하거나 새로 생성하도록 함)
    if "_id" in session_data:
        session_data.pop("_id")
    # 2. diningId를 기준으로 매칭하여 있으면 업데이트(Replace), 없으면 인서트
    result = await collection.update_one(
        {"diningId": request.dining_data.dining_id},
        {"$set": session_data},
        upsert=True
    )
    # 3. 결과 ID 반환
    if result.upserted_id:
        return str(result.upserted_id)
    else:
        # 이미 존재하여 업데이트된 경우, 기존 데이터의 ID를 조회하여 반환
        return str(existing["_id"]) if existing else None

async def get_session_by_dining_id(dining_id: str) -> Optional[DiningSession]:
    """diningId를 기반으로 DiningSession 조회"""
    db = get_db()
    collection = db["dining_sessions"]
    
    doc = await collection.find_one({"diningId": dining_id}) # camelCase 필드명 주의
    if doc:
        return DiningSession.model_validate(doc)
    return None

async def update_current_phase(dining_id: str) -> Optional[RecommendationsResponse]:
    """currentPhase를 1 증가시키고 결과 반환"""
    db = get_db()
    collection = db["dining_sessions"]
    
    # 0. 이미 완료된 세션인지 체크
    existing = await collection.find_one({"diningId": dining_id})
    if existing and existing.get("isCompleted"):
        return None

    result = await collection.find_one_and_update(
        {"diningId": dining_id},
        {"$inc": {"currentPhase": 1}},
        return_document=True
    )
    
    if not result:
        return None

    return_data = DiningSession.model_validate(result)
    return to_analyze_refresh_response(return_data)

async def finalize_dining_session(dining_id: int, restaurant_id: str) -> RestaurantFixResponse:
    """최종 식당을 확정하고 세션을 종료 상태로 변경"""
    db = get_db()
    collection = db["dining_sessions"]
    
    # 1. 기존 세션에서 해당 식당 정보가 후보군에 있었는지 확인하여 가져오기 (데이터 정합성)
    session_doc = await collection.find_one({"diningId": dining_id})
    if not session_doc:
        return RestaurantFixResponse(success=False, restaurant_id="")
    
    # 2. 후보군 중 선택된 식당 찾기
    selected_restaurant = next(
        (r for r in session_doc.get("restaurantCandidate", []) if r["restaurantId"] == restaurant_id), 
        None
    )

    # [수정 포인트] 후보군에 없는 식당일 경우 실패 반환
    if not selected_restaurant:
        return RestaurantFixResponse(success=False, restaurant_id="NOT_IN_CANDIDATES")
    
    # 3. 업데이트 수행
    await collection.update_one(
        {"diningId": dining_id},
        {
            "$set": {
                "isCompleted": True,
                "finalRestaurant": [selected_restaurant] 
            }
        }
    )
    
    return RestaurantFixResponse(success=True, restaurant_id=restaurant_id)