from typing import Any, Dict, List

from bson import ObjectId

from shared.database.db_manager import DBManager
from services.iterative_discussion.app.engine.state import ConsensusState
from services.iterative_discussion.app.utils.scoring import rank_restaurants


async def moderator_preselect(state: ConsensusState) -> dict:
    """Node 2: 식당 ID로 DB 조회 → 점수 기반 Top 10 선별."""
    restaurant_ids = state.get("filtered_restaurant_ids", [])
    user_data_list = state.get("user_data_list", [])

    if not restaurant_ids:
        return {
            "is_error": True,
            "error_message": "filtered_restaurant_ids가 비어있습니다.",
        }

    if not user_data_list:
        return {
            "is_error": True,
            "error_message": "user_data_list가 비어있습니다. Node 1을 먼저 실행하세요.",
        }

    # DB에서 식당 전체 문서 조회
    db = DBManager(col_name="restaurants")
    object_ids = [ObjectId(rid) for rid in restaurant_ids]
    restaurants: List[Dict[str, Any]] = await db.read_all({"_id": {"$in": object_ids}})

    if not restaurants:
        return {
            "is_error": True,
            "error_message": "DB에서 식당 데이터를 찾을 수 없습니다.",
        }

    # _id를 문자열로 변환
    for r in restaurants:
        if "_id" in r:
            r["_id"] = str(r["_id"])

    # 점수 기반 Top 10 선별
    candidate_pool = rank_restaurants(
        restaurants=restaurants,
        user_data_list=user_data_list,
        top_k=10,
    )

    return {"candidate_pool": candidate_pool}
