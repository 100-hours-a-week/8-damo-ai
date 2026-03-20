"""시맨틱 재정렬 노드.

유저 basePersona 임베딩과 Neo4j 리뷰 벡터 유사도로 filtered_restaurant를 재정렬한다.

Review 노드가 없는 Phase 1에서는 graceful fallback으로 동작하고,
리뷰 인덱싱 완료 후 자동으로 정상 동작한다.
"""

import logging
from typing import Any

from shared.database.db_manager import DBManager
from shared.database.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


async def _get_embedding(text: str) -> list[float]:
    """text-embedding-3-small으로 텍스트 임베딩을 생성한다."""
    from langchain_openai import OpenAIEmbeddings
    from shared.utils.config import get_settings

    settings = get_settings()
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.OPENAI_API_KEY,
    )
    return await embeddings.aembed_query(text)


async def _fetch_semantic_scores(
    embedding: list[float],
    restaurant_ids: list[str],
) -> dict[str, float]:
    """Neo4j 단일 쿼리로 식당별 평균 리뷰 유사도를 반환한다.

    Review 노드가 없거나 연결 실패 시 빈 dict를 반환한다.
    """
    driver = await Neo4jClient.get_driver()
    async with driver.session() as session:
        result = await session.run(
            """
            CALL db.index.vector.queryNodes(
                'review_embedding_index', 200, $embedding
            )
            YIELD node AS rev, score
            WHERE rev.restaurant_id IN $ids
            RETURN rev.restaurant_id AS rid, avg(score) AS avg_score
            """,
            embedding=embedding,
            ids=restaurant_ids,
        )
        return {r["rid"]: r["avg_score"] async for r in result}


async def semantic_rerank_node(state: dict[str, Any]) -> dict[str, Any]:
    """유저 페르소나 임베딩 기반 시맨틱 재정렬 노드.

    흐름:
    1. allergy_penalty 반영한 기본 final_score 계산 (Review 없어도 동작)
    2. users DB에서 basePersona 수집
    3. 그룹 페르소나 임베딩 생성 → Neo4j 유사도 조회 (실패 시 fallback)
    4. semantic_score 반영 final_score 재계산 → 내림차순 정렬
    """
    filtered = state.get("filtered_restaurant", [])
    if not filtered:
        logger.info("[SEMANTIC] filtered_restaurant 비어있음 → skip")
        return {}

    logger.info("[SEMANTIC] 시작: 식당=%d개, user_ids=%s", len(filtered), state.get("user_ids"))

    # 1. 기본 final_score (semantic=0 가정)
    for r in filtered:
        penalty = r.get("allergy_penalty", 0.0)
        r.setdefault("semantic_score", 0.0)
        r["final_score"] = r.get("total_score", 0.0) * 0.4 - penalty * 0.2
    logger.info("[SEMANTIC] 기본 final_score 계산 완료 (semantic=0 기준)")

    # 2. basePersona 수집
    db = DBManager(col_name="users")
    personas: list[str] = []
    for uid in state.get("user_ids", []):
        user = await db.read_one({"id": {"$in": [str(uid), int(uid)]}})
        if user and user.get("basePersona"):
            personas.append(user["basePersona"])
    logger.info("[SEMANTIC] basePersona 수집: %d/%d명 보유", len(personas), len(state.get("user_ids", [])))

    if not personas:
        logger.warning("[SEMANTIC] basePersona 없음 → total_score 기준 정렬로 fallback")
        return {
            "filtered_restaurant": sorted(
                filtered, key=lambda r: r["final_score"], reverse=True
            )
        }

    # 3. Neo4j 유사도 조회 (Review 없으면 빈 결과 → skip)
    try:
        logger.info("[SEMANTIC] 페르소나 임베딩 생성 시작")
        embedding = await _get_embedding(" ".join(personas))
        logger.info("[SEMANTIC] 페르소나 임베딩 생성 완료, Neo4j 유사도 조회 시작")
        restaurant_ids = [str(r["_id"]) for r in filtered]
        semantic_scores = await _fetch_semantic_scores(embedding, restaurant_ids)
        logger.info("[SEMANTIC] Neo4j 유사도 조회 완료: hit=%d/%d개", len(semantic_scores), len(restaurant_ids))
    except Exception as exc:
        logger.warning("[SEMANTIC] Neo4j 오류 또는 Review 미구축 → total_score 기준 정렬로 fallback: %s", exc)
        return {
            "filtered_restaurant": sorted(
                filtered, key=lambda r: r["final_score"], reverse=True
            )
        }

    # 4. semantic_score 반영 final_score 재계산
    for r in filtered:
        rid = str(r["_id"])
        sem = semantic_scores.get(rid, 0.0)
        penalty = r.get("allergy_penalty", 0.0)
        r["semantic_score"] = sem
        r["final_score"] = (
            r.get("total_score", 0.0) * 0.4
            + sem * 0.4
            - penalty * 0.2
        )

    reranked = sorted(filtered, key=lambda r: r["final_score"], reverse=True)
    logger.info("[SEMANTIC] 재정렬 완료: %d개, 상위 식당=%s (final_score=%.4f)",
                len(reranked),
                reranked[0].get("place_name", "unknown") if reranked else "없음",
                reranked[0].get("final_score", 0.0) if reranked else 0.0)
    return {"filtered_restaurant": reranked}
