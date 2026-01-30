"""토론 요약 노드"""

from typing import Dict, Any
from langchain_core.messages import AIMessage


async def summarize_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """현재 라운드의 토론 내용을 요약하는 노드

    Args:
        state: 현재 상태

    Returns:
        요약 메시지가 추가된 상태 업데이트
    """
    round_num = state.get("round", 1)
    messages = state.get("messages", [])

    # 현재 라운드의 에이전트 메시지만 추출
    agent_messages = [
        msg
        for msg in messages
        if hasattr(msg, "name") and msg.name and msg.name.startswith("agent_")
    ]

    # TODO: LLM을 사용하여 실제 요약 생성
    # 현재는 간단한 요약만 제공
    summary_message = AIMessage(
        content=f"""
        === 라운드 {round_num} 요약 ===
        
        총 {len(agent_messages)}명의 에이전트가 의견을 제시했습니다.
        
        주요 논점:
        - (LLM 기반 요약이 여기에 생성됩니다)
        
        다음 단계: 투표를 진행합니다.
        """,
        name="moderator",
    )

    return {"messages": [summary_message]}
