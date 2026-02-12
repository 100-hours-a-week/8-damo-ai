from shared.schemas.restaurant_fix_request import RestaurantFixRequest
from shared.schemas.restaurant_fix_response import RestaurantFixResponse
from shared.database.db_manager import DBManager
from shared.logging.logger import setup_logger
from datetime import datetime
from bson import ObjectId

# 로거 설정
logger = setup_logger("core_service_fix")

async def fix_task(request: RestaurantFixRequest) -> RestaurantFixResponse:
    db_manager = DBManager()
    db_manager.set_collection("dining_sessions")
    
    target_id = request.dining_data.dining_id
    restaurant_id = request.restaurant_id

    logger.info(f"Find Dining ID: {target_id} (Type: {type(target_id)})")

    # 1. 기존 세션 조회
    session_doc = await db_manager.read_one({
        "diningId": { "$in": [str(target_id), int(target_id)] }
    })
    
    if not session_doc:
        logger.warning(f"Session not found for diningId: {target_id}")
        return RestaurantFixResponse(success=False, restaurant_id="")

    # 2. 후보군 중 선택된 식당 찾기
    logger.info(f"Find Restaurant ID: {restaurant_id}")
    
    # 식당 ID가 ObjectId 문자열인 경우와 일반 문자열인 경우 모두 대응
    selected_restaurant = None
    for r in session_doc.get("restaurantCandidate", []):
        cand_id = r.get("restaurantId") or r.get("id") or r.get("_id")
        
        # ObjectId 객체인 경우와 문자열인 경우를 모두 체크
        try:
            # 입력받은 ID를 ObjectId로 변환하여 직접 비교 시도
            if cand_id == ObjectId(restaurant_id) or str(cand_id) == restaurant_id:
                selected_restaurant = r
                break
        except Exception:
            # ObjectId 변환이 불가능한 포맷인 경우 일반 문자열 비교 수행
            if str(cand_id) == restaurant_id:
                selected_restaurant = r
                break

    # 후보군에 없는 식당일 경우 실패 반환
    if not selected_restaurant:
        logger.warning(f"Restaurant {restaurant_id} not found in candidates for session {target_id}")
        return RestaurantFixResponse(success=False, restaurant_id="NOT_IN_CANDIDATES")

    # 3. 세션 업데이트 (조회된 문서의 _id를 사용하여 정확하게 업데이트)
    await db_manager.update_one(
        filter_query={"_id": session_doc["_id"]},
        update_data={
            "isCompleted": True,
            "finalRestaurant": [selected_restaurant],
            "updatedAt": datetime.now()
        }
    )

    return RestaurantFixResponse(
        success=True,
        restaurant_id=restaurant_id
    )