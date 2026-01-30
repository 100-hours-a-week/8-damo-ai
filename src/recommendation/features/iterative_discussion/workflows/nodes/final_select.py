"""최종 선정 노드"""

from typing import Dict, Any
from collections import Counter
from langchain_core.messages import AIMessage


async def final_select_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """합의에 도달한 경우 최종 식당을 선정하는 노드

    Args:
        state: 현재 상태

    Returns:
        최종 결정이 포함된 상태 업데이트
    """
    votes = state.get("votes", {})
    candidates = state.get("candidates", [])

    # 투표 결과 집계
    vote_counts = Counter(votes.values())

    # 가장 많은 표를 받은 식당 선정
    if vote_counts:
        final_restaurant_id = vote_counts.most_common(1)[0][0]
        vote_count = vote_counts[final_restaurant_id]
        total_votes = len(votes)

        # 선정된 식당 정보 찾기
        selected_restaurant = next(
            (c for c in candidates if c.get("id") == final_restaurant_id), None
        )

        restaurant_name = (
            selected_restaurant.get("name", "Unknown")
            if selected_restaurant
            else "Unknown"
        )

        final_message = AIMessage(
            content=f"""
            === 최종 결정 ===
            
            선정된 식당: {restaurant_name}
            투표 결과: {vote_count}/{total_votes}표
            
            토론이 성공적으로 완료되었습니다!
            """,
            name="moderator",
        )

        return {
            "final_decision": final_restaurant_id,
            "consensus_reached": True,
            "messages": [final_message],
        }

    # 투표가 없는 경우
    return {
        "final_decision": None,
        "consensus_reached": False,
    }
