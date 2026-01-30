"""주제/후보 발제 노드

ModeratorAgent를 사용하여 라운드 시작
"""

from typing import Dict, Any
from ...agents import ModeratorAgent


async def topic_proposal_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """현재 라운드의 주제와 후보를 발제하는 노드

    ModeratorAgent의 propose_topic 메서드를 사용하여
    LLM 기반 발제 메시지를 생성합니다.

    Args:
        state: 현재 상태

    Returns:
        발제 메시지가 추가된 상태 업데이트
    """
    round_num = state.get("round", 1)
    candidates = state.get("candidates", [])
    max_rounds = state.get("max_rounds", 3)
    messages = state.get("messages", [])

    # 이전 라운드 요약 추출 (2라운드 이상인 경우)
    previous_summary = None
    if round_num > 1:
        # 마지막 요약 메시지 찾기
        summary_messages = [
            msg
            for msg in messages
            if hasattr(msg, "name")
            and msg.name == "moderator"
            and "요약" in msg.content
        ]
        if summary_messages:
            previous_summary = summary_messages[-1].content

    # ModeratorAgent 생성 및 발제
    moderator = ModeratorAgent()
    proposal_message = await moderator.propose_topic(
        round_num=round_num,
        candidates=candidates,
        max_rounds=max_rounds,
        previous_summary=previous_summary,
    )

    return {"messages": [proposal_message]}
