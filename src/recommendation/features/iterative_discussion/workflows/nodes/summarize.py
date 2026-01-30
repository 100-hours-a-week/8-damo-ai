"""토론 요약 노드

ModeratorAgent를 사용하여 토론 내용을 요약합니다.
"""

from typing import Dict, Any
from ...agents import ModeratorAgent


async def summarize_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """현재 라운드의 토론 내용을 요약하는 노드

    ModeratorAgent의 summarize_discussion 메서드를 사용하여
    LLM 기반 토론 요약을 생성합니다.

    Args:
        state: 현재 상태

    Returns:
        요약 메시지가 추가된 상태 업데이트
    """
    round_num = state.get("round", 1)
    messages = state.get("messages", [])
    candidates = state.get("candidates", [])

    # ModeratorAgent 생성 및 요약
    moderator = ModeratorAgent()
    summary_message = await moderator.summarize_discussion(
        round_num=round_num, messages=messages, candidates=candidates
    )

    return {"messages": [summary_message]}
