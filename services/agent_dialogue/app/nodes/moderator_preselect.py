import logging
from typing import Any, Dict, List

from bson import ObjectId
from langchain_core.runnables import RunnableConfig
from langfuse import observe
from langfuse.decorators import langfuse_context

from shared.database.db_manager import DBManager
from services.agent_dialogue.app.engine.state import AgentDialogueState
from services.agent_dialogue.app.utils.scoring import rank_restaurants

logger = logging.getLogger(__name__)

_BATCH_SIZE = 5


@observe(name="moderator_preselect")
async def moderator_preselect(state: AgentDialogueState, config: RunnableConfig = None) -> dict:
    """Node 2: filtered_restaurant_ids에서 배치 5개를 DB 조회 → score 정렬."""
    correlation_id = ((config or {}).get("configurable") or {}).get("correlation_id")
    if correlation_id:
        langfuse_context.update_current_trace(session_id=correlation_id)

    all_ids = state.get("filtered_restaurant_ids", [])
    user_data_list = state.get("user_data_list", [])
    offset = state.get("restaurant_offset", 0)

    logger.info(
        "[Node2] moderator_preselect 시작: 전체=%d개, offset=%d",
        len(all_ids),
        offset,
    )

    if not all_ids:
        return {
            "is_error": True,
            "error_message": "filtered_restaurant_ids가 비어있습니다.",
        }

    if not user_data_list:
        return {
            "is_error": True,
            "error_message": "user_data_list가 비어있습니다. Node 1을 먼저 실행하세요.",
        }

    # 현재 배치 ID 슬라이싱
    batch_ids = all_ids[offset : offset + _BATCH_SIZE]
    if not batch_ids:
        return {
            "is_error": True,
            "error_message": f"offset={offset}부터 가져올 식당 ID가 없습니다.",
        }

    # DB에서 배치 식당 문서 조회
    db = DBManager(col_name="restaurants")
    try:
        object_ids = [ObjectId(rid) for rid in batch_ids]
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

    # score 기반 정렬 (배치 크기 내에서)
    dining_data = state.get("dining_data", {})
    candidate_pool = rank_restaurants(
        restaurants=restaurants,
        user_data_list=user_data_list,
        dining_data=dining_data,
        top_k=_BATCH_SIZE,
    )

    new_offset = offset + len(batch_ids)
    logger.info(
        "[Node2] moderator_preselect 완료: 후보=%d개, new_offset=%d",
        len(candidate_pool),
        new_offset,
    )
    return {
        "candidate_pool": candidate_pool,
        "restaurant_offset": new_offset,
        "restaurant_index": 0,
    }
