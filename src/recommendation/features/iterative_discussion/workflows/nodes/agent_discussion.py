"""에이전트 토론 노드"""

from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage


async def agent_discussion_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """에이전트들이 순차적으로 의견을 제시하는 노드

    Round-Robin 방식으로 각 에이전트가 발언합니다.
    TODO: PersonaAgent 클래스 구현 후 실제 LLM 호출로 교체

    Args:
        state: 현재 상태

    Returns:
        에이전트 발언이 추가된 상태 업데이트
    """
    user_ids = state.get("user_ids", [])
    candidates = state.get("candidates", [])
    messages = state.get("messages", [])

    new_messages: List[Any] = []

    # 각 에이전트가 순차적으로 발언
    for user_id in user_ids:
        # TODO: PersonaAgent를 사용하여 실제 의견 생성
        # 현재는 Mock 데이터 사용
        agent_message = AIMessage(
            content=f"""
            [User {user_id}의 의견]
            저는 {candidates[0].get("name", "Unknown")} 식당을 추천합니다.
            이유: (페르소나 기반 의견이 여기에 생성됩니다)
            """,
            name=f"agent_{user_id}",
        )
        new_messages.append(agent_message)

    return {"messages": new_messages}
