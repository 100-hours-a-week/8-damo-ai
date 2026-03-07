import logging
from typing import Any, Dict, List

from bson import ObjectId
from langfuse import observe

from shared.database.db_manager import DBManager
from services.iterative_discussion.app.engine.state import ConsensusState
from services.iterative_discussion.app.utils.scoring import rank_restaurants


logger = logging.getLogger(__name__)


@observe(name="moderator_preselect")
async def moderator_preselect(state: ConsensusState) -> dict:
    """Node 3: 식당 ID로 DB 조회 → 점수 기반 Top 10 선별."""
    restaurant_ids = state.get("filtered_restaurant_ids", [])
    user_data_list = state.get("user_data_list", [])
    rejected_ids = set(state.get("rejected_restaurant_ids", []))
    prev_pool = state.get("candidate_pool", [])
    logger.info(
        "[Node3] moderator_preselect 시작: 식당=%d개, 거부=%d개",
        len(restaurant_ids),
        len(rejected_ids),
    )

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
    try:
        object_ids = [ObjectId(rid) for rid in restaurant_ids]
        restaurants: List[Dict[str, Any]] = await db.read_all({"_id": {"$in": object_ids}})
    except Exception as exc:
        logger.warning("식당 DB 조회 실패", exc_info=True)
        return {"is_error": True, "error_message": f"식당 DB 조회 실패: {exc}"}

    if not restaurants:
        return {
            "is_error": True,
            "error_message": "DB에서 식당 데이터를 찾을 수 없습니다.",
        }

    # _id를 문자열로 변환
    for r in restaurants:
        if "_id" in r:
            r["_id"] = str(r["_id"])

    # 거부된 식당 제외
    if rejected_ids:
        restaurants = [r for r in restaurants if str(r.get("_id", "")) not in rejected_ids]

    # 점수 기반 Top 10 선별
    candidate_pool = rank_restaurants(
        restaurants=restaurants,
        user_data_list=user_data_list,
        top_k=10,
    )

    # 후보 교체 피드백 생성 (재선별 시에만)
    moderator_feedback = state.get("moderator_feedback", "")
    if prev_pool and rejected_ids:
        prev_ids = {str(r.get("_id", "")) for r in prev_pool}
        new_ids = {str(r.get("_id", "")) for r in candidate_pool}
        added = [
            r for r in candidate_pool
            if str(r.get("_id", "")) in (new_ids - prev_ids)
        ]
        removed = [
            r for r in prev_pool
            if str(r.get("_id", "")) in rejected_ids
        ]
        if removed or added:
            lines = []
            for r in removed:
                lines.append(f"- 제외: {r.get('place_name', '?')}")
            for r in added:
                lines.append(f"- 신규: {r.get('place_name', '?')} ({r.get('category_detail', '')})")
            swap_text = "\n".join(lines)
            moderator_feedback = f"{moderator_feedback}\n\n[후보 교체 안내]\n{swap_text}".strip()

    logger.info(
        "[Node3] moderator_preselect 완료: 후보=%d개 선별",
        len(candidate_pool),
    )
    return {
        "candidate_pool": candidate_pool,
        "rejected_restaurant_ids": [],
        "moderator_feedback": moderator_feedback,
    }
