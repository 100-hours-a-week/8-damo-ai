"""RAG reason retriever — Neo4j 버전.

Neo4j 벡터 인덱스를 이용한 리뷰 검색.
Review 노드가 없거나 driver=None이면 빈 리스트를 반환한다 (graceful fallback).

generator.py 하위 호환을 위해 Document 객체로 wrapping하여 반환한다.
"""
import logging
from typing import Any

from langchain_core.documents import Document

logger = logging.getLogger("faststream")


async def _get_embedding(text: str) -> list[float]:
    """text-embedding-3-small로 쿼리 임베딩을 생성한다."""
    from langchain_openai import OpenAIEmbeddings
    from shared.utils.config import get_settings

    settings = get_settings()
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.OPENAI_API_KEY,
    )
    return await embeddings.aembed_query(text)


def build_query(restaurant: dict[str, Any]) -> str:
    """식당 메타데이터에서 의미론적 검색 쿼리를 생성한다."""
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
    driver: Any,  # Neo4j AsyncDriver 또는 None (generator.py 호환: 2번째 positional 인수)
    top_k: int = 5,
) -> list[Document]:
    """Neo4j 벡터 인덱스로 관련 리뷰를 검색한다.

    Review 노드가 없거나 driver=None이면 빈 리스트를 반환한다.
    반환값은 generator.py 호환을 위해 list[Document] 형식이다.
    """
    if driver is None:
        logger.warning("[RETRIEVER] driver=None → 리뷰 검색 skip")
        return []

    restaurant_id = str(restaurant.get("_id", ""))
    if not restaurant_id:
        logger.warning("[RETRIEVER] restaurant_id 없음 → 리뷰 검색 skip")
        return []

    query_text = build_query(restaurant)
    if not query_text.strip():
        logger.warning("[RETRIEVER] query_text 비어있음 → 리뷰 검색 skip: restaurant_id=%s", restaurant_id)
        return []

    try:
        logger.info("[RETRIEVER] 리뷰 검색 시작: restaurant_id=%s, query=%s", restaurant_id, query_text[:50])
        embedding = await _get_embedding(query_text)
        async with driver.session() as session:
            result = await session.run(
                """
                CALL db.index.vector.queryNodes(
                    'review_embedding_index', $fetch_k, $embedding
                )
                YIELD node AS rev, score
                WHERE rev.restaurant_id = $restaurant_id
                RETURN rev.review_text
                ORDER BY score DESC
                LIMIT $top_k
                """,
                fetch_k=top_k * 3,
                embedding=embedding,
                restaurant_id=restaurant_id,
                top_k=top_k,
            )
            records = [row async for row in result]

        docs = [Document(page_content=r["rev.review_text"]) for r in records]
        logger.info("[RETRIEVER] 리뷰 검색 완료: restaurant_id=%s, 결과=%d건", restaurant_id, len(docs))
        for idx, doc in enumerate(docs):
            logger.debug("[RETRIEVER] 리뷰[%d]: %s", idx, doc.page_content[:100])
        return docs

    except Exception as exc:
        logger.warning("[RETRIEVER] 리뷰 검색 실패: restaurant_id=%s, error=%s", restaurant_id, exc)
        return []
