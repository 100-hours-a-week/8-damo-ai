import asyncio
import logging
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langfuse import get_client as _get_lf_client, observe
from motor.motor_asyncio import AsyncIOMotorDatabase

from shared.database.db_manager import DBManager
from shared.schemas.stream_schema import FinalRestaurant
from shared.utils.config import get_settings
from .client import get_vector_store
from .retriever import retrieve_reviews
from .prompts import RAG_REASON_SYSTEM_PROMPT, RAG_REASON_USER_PROMPT

logger = logging.getLogger("faststream")


@observe(name="rag_reason_generation", as_type="generation")
async def generate_reason_for_restaurant(
    restaurant_id: str,
    summary: str,
    dining_context: dict[str, Any],
    llm: ChatOpenAI,
    vector_store: Any,
    restaurants_collection: Any,
) -> tuple[str, str]:
    """Return (restaurant_id, reasoning_description) using RAG.

    MongoDB/Qdrant 조회 실패 시에도 LLM 호출을 시도하며,
    LLM 자체 실패 시에만 generic fallback을 반환한다.

    Args:
        restaurants_collection: A Motor collection handle (no shared mutable state).
    """
    GENERIC_FALLBACK = "예산과 위치를 고려한 최적의 회식 장소입니다."

    # MongoDB 조회 시도 — 실패해도 LLM 호출은 계속
    restaurant = None
    try:
        oid = ObjectId(restaurant_id)
        restaurant = await restaurants_collection.find_one({"_id": oid})
    except (InvalidId, Exception):
        pass

    if restaurant:
        reviews = []
        if vector_store is not None:
            try:
                reviews = await retrieve_reviews(restaurant, vector_store)
            except Exception:
                pass
        review_excerpts = (
            "\n".join(f"- {doc.page_content[:200]}" for doc in reviews)
            if reviews
            else "리뷰 정보가 없습니다."
        )
        menus = restaurant.get("menus", [])
        top_menus = ", ".join(
            m.get("title") or m.get("name", "") for m in menus[:3] if m.get("title") or m.get("name")
        )
        place_name = restaurant.get("place_name") or restaurant.get("name", "")
        category_detail = restaurant.get("category_detail", "")
        logger.info(
            "[RAG_GEN] 식당 정보 로드: id=%s, name=%s, category=%s, menus=%s, reviews=%d건",
            restaurant_id, place_name, category_detail, top_menus, len(reviews),
        )
        for idx, doc in enumerate(reviews):
            logger.debug("[RAG_GEN] 리뷰[%d] 사용: %s", idx, doc.page_content[:100])
    else:
        review_excerpts = "리뷰 정보가 없습니다."
        top_menus = "정보 없음"
        place_name = summary
        category_detail = ""

    try:
        user_prompt = RAG_REASON_USER_PROMPT.format(
            budget=dining_context.get("budget", ""),
            member_count=dining_context.get("member_count", ""),
            dining_date=dining_context.get("dining_date", ""),
            place_name=place_name,
            category_detail=category_detail,
            top_menus=top_menus,
            review_excerpts=review_excerpts,
        )
        messages = [
            SystemMessage(content=RAG_REASON_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = await llm.ainvoke(messages)
        reason = response.content.strip()
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            _get_lf_client().update_current_generation(
                model=llm.model_name,
                usage_details={
                    "input_tokens": response.usage_metadata.get("input_tokens"),
                    "output_tokens": response.usage_metadata.get("output_tokens"),
                },
            )
        return restaurant_id, reason if reason else GENERIC_FALLBACK

    except Exception as e:
        logger.warning(f"generate_reason_for_restaurant LLM failed for {restaurant_id}: {e}")
        return restaurant_id, GENERIC_FALLBACK


async def rag_reason_task(
    final_restaurants: list[FinalRestaurant],
    dining_context: dict[str, Any],
) -> dict[str, str]:
    """Generate RAG-based reasoning for all restaurants concurrently.

    Returns {restaurant_id: reasoning_description}.
    Individual failures fall back to item.summary.
    """
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.4,
        api_key=settings.OPENAI_API_KEY,
    )

    try:
        vector_store = await get_vector_store()
    except Exception as e:
        logger.warning(f"rag_reason_task: Qdrant 연결 실패, 리뷰 없이 진행: {e}")
        vector_store = None

    # Single DBManager; access the collection directly to avoid set_collection race
    db = DBManager()
    restaurants_collection = db.db["restaurants"]

    tasks = [
        generate_reason_for_restaurant(
            restaurant_id=item.restaurant_id,
            summary=item.summary or "",
            dining_context=dining_context,
            llm=llm,
            vector_store=vector_store,
            restaurants_collection=restaurants_collection,
        )
        for item in final_restaurants
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    _GENERIC_FALLBACK = "예산과 위치를 고려한 최적의 회식 장소입니다."
    reason_map: dict[str, str] = {}
    for item, result in zip(final_restaurants, results):
        if isinstance(result, Exception):
            logger.warning(f"rag_reason_task: exception for {item.restaurant_id}: {result}")
            reason_map[item.restaurant_id] = _GENERIC_FALLBACK
        else:
            rid, reason = result
            reason_map[rid] = reason

    return reason_map
