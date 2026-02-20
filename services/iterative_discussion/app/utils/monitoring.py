from typing import Any, Dict

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from shared.utils.config import settings


def init_consensus_trace(
    session_id: str = "",
    metadata: Dict[str, Any] | None = None,
) -> str:
    """추천 사이클 시작 시 부모 trace ID를 생성하여 반환.

    이 trace_id를 state에 저장하면, 이후 모든 노드의 LLM 호출이
    이 trace 아래 span으로 중첩된다.

    Langfuse v3: client.trace() 제거됨 → create_trace_id() 사용.
    """
    if not settings.LANGFUSE_PUBLIC_KEY:
        return ""

    return Langfuse.create_trace_id()


def create_langfuse_handler(
    trace_id: str,
    name: str,
    user_id: str = "",
    metadata: Dict[str, Any] | None = None,
) -> CallbackHandler | None:
    """부모 trace 아래에 span으로 달리는 Langfuse 핸들러를 생성.

    Langfuse v3: trace_context dict로 trace_id를 전달.

    Args:
        trace_id: init_consensus_trace()에서 반환된 부모 trace ID
        name: 이 span의 이름 (예: "dialogue_round1_유저A")
        user_id: 페르소나/유저 ID (v3에서는 update_trace로 별도 설정)
        metadata: 추가 메타데이터 (v3에서는 update_trace로 별도 설정)
    """
    if not trace_id or not settings.LANGFUSE_PUBLIC_KEY:
        return None

    return CallbackHandler(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_BASE_URL,
        trace_context={"trace_id": trace_id},
    )
