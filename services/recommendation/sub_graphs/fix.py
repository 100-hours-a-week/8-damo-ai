import logging
from shared.schemas.stream_schema import RestaurantConfirmedPayload
from shared.database.db_manager import DBManager
from datetime import datetime
from bson import ObjectId

# 로거 설정
logger = logging.getLogger("faststream") 

async def fix_task(request: RestaurantConfirmedPayload):
    db_manager = DBManager()
    db_manager.set_collection("dining_sessions")
    
    dining_id = request.payload.dining_data.dining_id
    restaurant_id = request.payload.restaurant_id

    logger.info(f"Find Dining ID: {dining_id} (type: {type(dining_id)})")
    logger.info(f"Find Restaurant ID: {restaurant_id} (type: {type(restaurant_id)})")

    # 1. 기존 세션 조회
    session_doc = await db_manager.read_one({
        "diningId": { "$in": [str(dining_id), int(dining_id)] }
    })
    
    if not session_doc:
        logger.warning(f"Session not found for diningId: {dining_id}")
        return

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
        logger.warning(f"Restaurant {restaurant_id} not found in candidates for session {dining_id}")
        return

    # 3. 세션 업데이트 (최종 확정 및 상태 메시지 기록)
    await db_manager.update_one_with_command(
        {"_id": session_doc["_id"]},
        {
            "$set": {
                "isCompleted": True,
                "finalRestaurant": selected_restaurant, # 리스트가 아닌 단일 객체 권장 (스키마 확인 필요)
                "restaurantCandidate": [],             # 후보군 비우기
                "updatedAt": datetime.now()
            },
            "$push": {
                "statusMessage": {
                    "msg": f"최종 식당이 [{selected_restaurant.get('name', '확정된 장소')}]로 확정되었습니다.",
                    "timestamp": datetime.now().isoformat()
                }
            }
        }
    )

    return