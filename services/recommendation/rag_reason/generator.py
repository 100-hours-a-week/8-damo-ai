import asyncio
import logging
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from motor.motor_asyncio import AsyncIOMotorDatabase

from shared.database.db_manager import DBManager
from shared.schemas.stream_schema import FinalRestaurant
from shared.utils.config import get_settings
from .client import get_vector_store
from .retriever import retrieve_reviews
from .prompts import RAG_REASON_SYSTEM_PROMPT, RAG_REASON_USER_PROMPT

logger = logging.getLogger("faststream")


async def generate_reason_for_restaurant(
    restaurant_id: str,
    summary: str,
    dining_context: dict[str, Any],
    llm: ChatOpenAI,
    vector_store: Any,
    restaurants_collection: Any,
) -> tuple[str, str]:
    """Return (restaurant_id, reasoning_description) using RAG, fallback to summary.

    Args:
        restaurants_collection: A Motor collection handle (no shared mutable state).
    """
    try:
        try:
            oid = ObjectId(restaurant_id)
        except InvalidId:
            logger.error(f"Invalid restaurant ObjectId: {restaurant_id}")
            return restaurant_id, summary

        restaurant = await restaurants_collection.find_one({"_id": oid})
        if not restaurant:
            return restaurant_id, summary

        reviews = await retrieve_reviews(restaurant, vector_store)

        if reviews:
            review_excerpts = "\n".join(
                f"- {doc.page_content[:200]}" for doc in reviews
            )
        else:
            review_excerpts = "리뷰 정보가 없습니다."

        menus = restaurant.get("menus", [])
        top_menus = ", ".join(
            m.get("title") or m.get("name", "") for m in menus[:3] if m.get("title") or m.get("name")
        )

        user_prompt = RAG_REASON_USER_PROMPT.format(
            budget=dining_context.get("budget", ""),
            member_count=dining_context.get("member_count", ""),
            dining_date=dining_context.get("dining_date", ""),
            place_name=restaurant.get("place_name") or restaurant.get("name", ""),
            category_detail=restaurant.get("category_detail", ""),
            top_menus=top_menus or "정보 없음",
            review_excerpts=review_excerpts,
        )

        messages = [
            SystemMessage(content=RAG_REASON_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = await llm.ainvoke(messages)
        reason = response.content.strip()
        return restaurant_id, reason if reason else summary

    except Exception as e:
        logger.warning(f"generate_reason_for_restaurant failed for {restaurant_id}: {e}")
        return restaurant_id, summary


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
        logger.warning(f"rag_reason_task: failed to connect to Qdrant: {e}")
        return {item.restaurant_id: item.summary or "" for item in final_restaurants}

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

    reason_map: dict[str, str] = {}
    for item, result in zip(final_restaurants, results):
        if isinstance(result, Exception):
            logger.warning(f"rag_reason_task: exception for {item.restaurant_id}: {result}")
            reason_map[item.restaurant_id] = item.summary or ""
        else:
            rid, reason = result
            reason_map[rid] = reason

    return reason_map
