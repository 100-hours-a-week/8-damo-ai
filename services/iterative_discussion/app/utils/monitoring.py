from typing import Any, Dict

from langfuse.langchain import CallbackHandler
from shared.monitoring.langfuse_client import get_langfuse_client
from shared.utils.config import settings


def init_consensus_trace(
    session_id: str = "",
    metadata: Dict[str, Any] | None = None,
) -> str:
    """추천 사이클 시작 시 부모 trace를 생성하고 trace_id를 반환.

    이 trace_id를 state에 저장하면, 이후 모든 노드의 LLM 호출이
    이 trace 아래 span으로 중첩된다.
    """
    if not settings.LANGFUSE_PUBLIC_KEY:
        return ""

    client = get_langfuse_client()
    trace = client.trace(
        name="consensus_cycle",
        session_id=session_id or None,
        metadata=metadata or {},
        tags=["consensus"],
    )
    return trace.id


def create_langfuse_handler(
    trace_id: str,
    name: str,
    user_id: str = "",
    metadata: Dict[str, Any] | None = None,
) -> CallbackHandler | None:
    """부모 trace 아래에 span으로 달리는 Langfuse 핸들러를 생성.

    Args:
        trace_id: init_consensus_trace()에서 반환된 부모 trace ID
        name: 이 span의 이름 (예: "dialogue_round1_유저A")
        user_id: 페르소나/유저 ID
        metadata: 추가 메타데이터
    """
    if not trace_id or not settings.LANGFUSE_PUBLIC_KEY:
        return None

    return CallbackHandler(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_BASE_URL,
        trace_id=trace_id,
        name=name,
        user_id=user_id or None,
        metadata=metadata or {},
    )
