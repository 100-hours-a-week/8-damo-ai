import asyncio
import logging
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langfuse import observe

from services.iterative_discussion.app.engine.llm_factory import get_chat_llm
from services.iterative_discussion.app.engine.state import ConsensusState
from services.iterative_discussion.app.prompts.reason_templates import (
    REASON_GENERATOR_SYSTEM_PROMPT,
    REASON_GENERATOR_USER_PROMPT,
)
from shared.database.db_manager import DBManager

logger = logging.getLogger(__name__)


async def _generate_reason(
    restaurant_id: str,
    place_name: str,
    discussion_reason: str,
    dining_data: Dict[str, Any],
    llm: Any,
    restaurants_collection: Any,
) -> tuple[str, str]:
    """LLM으로 추천이유를 생성. 실패 시 discussion_reason으로 fallback."""
    try:
        from bson import ObjectId
        from bson.errors import InvalidId

        try:
            oid = ObjectId(restaurant_id)
        except InvalidId:
            return restaurant_id, discussion_reason

        restaurant = await restaurants_collection.find_one({"_id": oid})
        if not restaurant:
            return restaurant_id, discussion_reason

        menus = restaurant.get("menus", [])
        top_menus = ", ".join(
            m.get("title") or m.get("name", "")
            for m in menus[:3]
            if m.get("title") or m.get("name")
        )

        budget = dining_data.get("budget", "")
        dining_date = dining_data.get("dining_date", "")
        # dining_data에 user_ids가 없으므로 member_count는 별도로 전달받지 않음
        member_count = dining_data.get("member_count", "")

        user_prompt = REASON_GENERATOR_USER_PROMPT.format(
            budget=budget,
            member_count=member_count,
            dining_date=dining_date,
            place_name=restaurant.get("place_name") or restaurant.get("name") or place_name,
            category_detail=restaurant.get("category_detail", ""),
            top_menus=top_menus or "정보 없음",
            discussion_reason=discussion_reason or "토론에서 선정됨",
        )

        messages = [
            SystemMessage(content=REASON_GENERATOR_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = await llm.ainvoke(messages)
        reason = response.content.strip()
        return restaurant_id, reason if reason else discussion_reason

    except Exception as e:
        logger.warning(f"_generate_reason failed for {restaurant_id}: {e}")
        return restaurant_id, discussion_reason


@observe(name="reason_generator")
async def reason_generator(state: ConsensusState) -> dict:
    """Node 7: 최종 선정 식당에 대해 LLM으로 추천이유 생성."""
    final_selection: List[Dict[str, Any]] = state.get("final_selection", [])
    dining_data: Dict[str, Any] = state.get("dining_data", {})
    user_ids: List[int] = state.get("user_ids", [])

    if not final_selection:
        logger.warning("[Node7] final_selection이 비어있어 reason_generator를 건너뜁니다.")
        return {}

    # member_count를 dining_data에 주입
    dining_data_with_count = {**dining_data, "member_count": len(user_ids)}

    logger.info("[Node7] reason_generator 시작: %d개 식당", len(final_selection))

    llm = get_chat_llm(temperature=0.4)
    db = DBManager()
    restaurants_collection = db.db["restaurants"]

    tasks = [
        _generate_reason(
            restaurant_id=item.get("restaurant_id", ""),
            place_name=item.get("place_name", ""),
            discussion_reason=item.get("reason", ""),
            dining_data=dining_data_with_count,
            llm=llm,
            restaurants_collection=restaurants_collection,
        )
        for item in final_selection
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    updated_selection = []
    for item, result in zip(final_selection, results):
        updated_item = dict(item)
        if isinstance(result, Exception):
            logger.warning(
                "[Node7] reason 생성 실패 (fallback): %s — %s",
                item.get("restaurant_id"),
                result,
            )
        else:
            _, reason = result
            updated_item["reason"] = reason
        updated_selection.append(updated_item)

    logger.info("[Node7] reason_generator 완료: %d개 추천이유 생성", len(updated_selection))
    return {"final_selection": updated_selection}
