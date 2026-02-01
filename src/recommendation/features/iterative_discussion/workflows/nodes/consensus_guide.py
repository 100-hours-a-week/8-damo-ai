"""합의 유도 노드

ModeratorAgent를 사용하여 투표 전 합의를 유도합니다.
"""

from typing import Dict, Any
from ...agents import ModeratorAgent


async def consensus_guide_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """투표 전 합의를 유도하는 노드

    ModeratorAgent의 guide_consensus 메서드를 사용하여
    참여자들이 합의에 도달할 수 있도록 유도합니다.

    Args:
        state: 현재 상태

    Returns:
        합의 유도 메시지가 추가된 상태 업데이트
    """
    round_num = state.get("round", 1)
    max_rounds = state.get("max_rounds", 3)
    messages = state.get("messages", [])
    candidates = state.get("filtered_restaurants", [])
    votes = state.get("votes", {})

    # ModeratorAgent 생성 및 합의 유도
    moderator = ModeratorAgent()
    consensus_message = await moderator.guide_consensus(
        round_num=round_num,
        max_rounds=max_rounds,
        messages=messages,
        candidates=candidates,
        votes=votes if votes else None,
    )

    return {"messages": [consensus_message]}
