"""투표 노드"""

from typing import Dict, Any
from collections import Counter
from langchain_core.messages import AIMessage


async def vote_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """각 에이전트의 투표를 수집하고 집계하는 노드

    최종 선정된 5개 후보 중에서 투표를 진행합니다.

    Args:
        state: 현재 상태

    Returns:
        투표 결과가 업데이트된 상태
    """
    user_ids = state.get("user_ids", [])
    final_candidates = state.get("final_candidates", [])

    # final_candidates가 없으면 candidates 사용 (하위 호환성)
    if not final_candidates:
        final_candidates = state.get("candidates", [])

    votes = {}

    # TODO: PersonaAgent를 사용하여 실제 투표 수집
    # 현재는 Mock 투표 데이터 사용
    for user_id in user_ids:
        # 첫 번째 후보에 투표 (임시)
        if final_candidates:
            votes[f"agent_{user_id}"] = final_candidates[0].get("id", "unknown")

    # 투표 결과 집계
    vote_counts = Counter(votes.values())

    # 투표 결과를 식당 이름과 함께 표시
    vote_details = []
    for rest_id, count in vote_counts.most_common():
        restaurant = next(
            (c for c in final_candidates if c.get("id") == rest_id), {"name": "Unknown"}
        )
        vote_details.append(f"  - {restaurant.get('name')}: {count}표")

    vote_message = AIMessage(
        content=f"""
        === 투표 결과 ===
        
        최종 {len(final_candidates)}개 후보 중 투표 진행:
        
        투표 현황:
        {chr(10).join(vote_details)}
        
        총 투표 수: {len(votes)}명
        """,
        name="moderator",
    )

    return {"votes": votes, "messages": [vote_message]}
