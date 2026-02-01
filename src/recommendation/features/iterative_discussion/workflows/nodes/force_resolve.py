"""강제 해결 노드"""

from typing import Dict, Any
from collections import Counter
from langchain_core.messages import AIMessage


async def force_resolve_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """최대 라운드에 도달했지만 합의에 이르지 못한 경우 강제로 결정하는 노드

    투표 기반으로 가장 많은 표를 받은 식당을 선정합니다.

    Args:
        state: 현재 상태

    Returns:
        강제 결정이 포함된 상태 업데이트
    """
    votes = state.get("votes", {})
    candidates = state.get("candidates", [])
    max_rounds = state.get("max_rounds", 3)

    # 투표 결과 집계
    vote_counts = Counter(votes.values())

    if vote_counts:
        # 가장 많은 표를 받은 식당 선정
        final_restaurant_id, vote_count = vote_counts.most_common(1)[0]
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

        force_message = AIMessage(
            content=f"""
            === 강제 해결 ===
            
            최대 라운드({max_rounds})에 도달하여 투표 기반으로 결정합니다.
            
            선정된 식당: {restaurant_name}
            투표 결과: {vote_count}/{total_votes}표
            
            완전한 합의에는 이르지 못했지만, 다수결로 결정되었습니다.
            """,
            name="moderator",
        )

        return {
            "final_decision": final_restaurant_id,
            "consensus_reached": False,  # 강제 해결이므로 False
            "messages": [force_message],
        }

    # 투표가 없는 경우 첫 번째 후보 선택
    if candidates:
        fallback_id = candidates[0].get("id", "unknown")
        fallback_name = candidates[0].get("name", "Unknown")

        fallback_message = AIMessage(
            content=f"""
            === 기본 선택 ===
            
            투표 결과가 없어 첫 번째 후보를 선택합니다: {fallback_name}
            """,
            name="moderator",
        )

        return {
            "final_decision": fallback_id,
            "consensus_reached": False,
            "messages": [fallback_message],
        }

    return {
        "final_decision": None,
        "consensus_reached": False,
    }
