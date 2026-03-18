from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import AsyncQdrantClient

from shared.utils.config import get_settings

_vector_store: QdrantVectorStore | None = None


def get_embeddings() -> OpenAIEmbeddings:
    settings = get_settings()
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.OPENAI_API_KEY,
    )


async def get_qdrant_client() -> AsyncQdrantClient:
    settings = get_settings()
    return AsyncQdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
    )


async def get_vector_store() -> QdrantVectorStore:
    """Return a module-level singleton QdrantVectorStore to avoid connection leaks."""
    global _vector_store
    if _vector_store is None:
        settings = get_settings()
        client = await get_qdrant_client()
        embeddings = get_embeddings()
        _vector_store = QdrantVectorStore(
            client=client,
            collection_name=settings.QDRANT_COLLECTION_NAME,
            embedding=embeddings,
            content_payload_key="review_text",
        )
    return _vector_store
