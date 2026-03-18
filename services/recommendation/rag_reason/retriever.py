import logging
from typing import Any

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client.models import Filter, FieldCondition, MatchValue

logger = logging.getLogger("faststream")


def build_query(restaurant: dict[str, Any]) -> str:
    """Build semantic search query from restaurant metadata."""
    parts: list[str] = []

    place_name = restaurant.get("place_name") or restaurant.get("name", "")
    if place_name:
        parts.append(place_name)

    category = restaurant.get("category_detail", "")
    if category:
        parts.append(category)

    menus = restaurant.get("menus", [])
    menu_titles = [m.get("title") or m.get("name", "") for m in menus[:3]]
    parts.extend(t for t in menu_titles if t)

    keywords = restaurant.get("restaurant_review_keywords", [])
    keyword_texts = [k.get("keyword", "") for k in keywords[:5]]
    parts.extend(t for t in keyword_texts if t)

    return " ".join(parts)


async def retrieve_reviews(
    restaurant: dict[str, Any],
    vector_store: QdrantVectorStore,
    top_k: int = 5,
) -> list[Document]:
    """Retrieve relevant reviews for a restaurant via semantic search with ID filter."""
    restaurant_id = str(restaurant.get("_id", ""))
    if not restaurant_id:
        return []

    query = build_query(restaurant)
    if not query.strip():
        return []

    try:
        payload_filter = Filter(
            must=[
                FieldCondition(
                    key="restaurant_id",
                    match=MatchValue(value=restaurant_id),
                )
            ]
        )
        docs = await vector_store.asimilarity_search(
            query=query,
            k=top_k,
            filter=payload_filter,
        )
        return docs
    except Exception as e:
        logger.warning(f"retrieve_reviews failed for {restaurant_id}: {e}")
        return []
