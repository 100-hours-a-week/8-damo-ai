"""투표 노드"""

from typing import Dict, Any
from collections import Counter
from langchain_core.messages import AIMessage


async def vote_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """각 에이전트의 투표를 수집하고 집계하는 노드

    Args:
        state: 현재 상태

    Returns:
        투표 결과가 업데이트된 상태
    """
    user_ids = state.get("user_ids", [])
    candidates = state.get("candidates", [])

    votes = {}

    # TODO: PersonaAgent를 사용하여 실제 투표 수집
    # 현재는 Mock 투표 데이터 사용
    for user_id in user_ids:
        # 첫 번째 후보에 투표 (임시)
        if candidates:
            votes[f"agent_{user_id}"] = candidates[0].get("id", "unknown")

    # 투표 결과 집계
    vote_counts = Counter(votes.values())

    vote_message = AIMessage(
        content=f"""
        === 투표 결과 ===
        
        투표 현황:
        {dict(vote_counts)}
        
        총 투표 수: {len(votes)}
        """,
        name="moderator",
    )

    return {"votes": votes, "messages": [vote_message]}
