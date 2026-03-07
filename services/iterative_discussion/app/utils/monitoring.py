import logging
import os
from importlib.metadata import version

from shared.utils.config import settings

logger = logging.getLogger(__name__)

# Langfuse SDK는 os.environ에서 키를 읽음
# pydantic-settings는 .env를 os.environ에 반영하지 않으므로 직접 주입
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.LANGFUSE_PUBLIC_KEY)
os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.LANGFUSE_SECRET_KEY)
os.environ.setdefault("LANGFUSE_HOST", settings.LANGFUSE_BASE_URL)

logger.info(
    "[Langfuse] 초기화: version=%s, public_key=%s, host=%s",
    version("langfuse"),
    "SET" if settings.LANGFUSE_PUBLIC_KEY else "MISSING",
    settings.LANGFUSE_BASE_URL or "MISSING",
)


def init_consensus_trace(session_id: str, metadata: dict) -> str:
    from langfuse import get_client

    trace = get_client().trace(
        name="consensus_flow",
        session_id=session_id,
        metadata=metadata,
    )
    return trace.id
