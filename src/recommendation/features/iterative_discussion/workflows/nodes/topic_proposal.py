"""주제/후보 발제 노드"""

from typing import Dict, Any
from langchain_core.messages import AIMessage


async def topic_proposal_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """현재 라운드의 주제와 후보를 발제하는 노드

    Args:
        state: 현재 상태

    Returns:
        발제 메시지가 추가된 상태 업데이트
    """
    round_num = state.get("round", 1)
    candidates = state.get("candidates", [])

    # 후보 식당 정보 요약
    candidate_summary = "\n".join(
        [
            f"- {i + 1}. {candidate.get('name', 'Unknown')} "
            f"(카테고리: {candidate.get('category', 'N/A')}, "
            f"위치: {candidate.get('location', 'N/A')})"
            for i, candidate in enumerate(candidates)
        ]
    )

    proposal_message = AIMessage(
        content=f"""
        === 라운드 {round_num} 시작 ===
        
        현재 후보 식당 목록:
        {candidate_summary}
        
        각 에이전트는 자신의 선호도와 제약사항을 고려하여 의견을 제시해주세요.
        """,
        name="moderator",
    )

    return {"messages": [proposal_message]}
