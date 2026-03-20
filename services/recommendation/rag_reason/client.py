"""RAG reason client — Neo4j 버전.

Qdrant 의존성을 제거하고 Neo4j 드라이버를 반환한다.
generator.py 하위 호환을 위해 get_vector_store 별칭을 유지한다.
"""
import logging

from shared.database.neo4j_client import Neo4jClient

logger = logging.getLogger("faststream")


async def get_neo4j_driver():
    """Neo4j 드라이버를 반환한다. 연결 실패 시 None 반환 (graceful fallback)."""
    try:
        driver = await Neo4jClient.get_driver()
        logger.info("[RAG_CLIENT] Neo4j 드라이버 연결 성공")
        return driver
    except Exception as exc:
        logger.warning("[RAG_CLIENT] Neo4j 연결 실패 → fallback: %s", exc)
        return None


# generator.py가 get_vector_store를 import하므로 별칭 유지
get_vector_store = get_neo4j_driver
