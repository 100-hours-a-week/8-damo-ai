"""최종 추천 식당 5개 선정 노드"""

from typing import Dict, Any, List
from langchain_core.messages import AIMessage
from ...agents import ModeratorAgent


async def final_select_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """토론 후 최종 추천할 식당 5개를 선정하는 노드

    ModeratorAgent를 사용하여 토론 내용을 분석하고
    에이전트들의 선호도에 따라 식당을 정렬합니다.

    Args:
        state: 현재 상태

    Returns:
        filtered_restaurants (정렬됨)가 업데이트된 상태
    """
    candidates = state.get("filtered_restaurants", [])
    messages = state.get("messages", [])

    # ModeratorAgent 생성 및 순위 선정
    moderator = ModeratorAgent()
    ranking_result = await moderator.rank_candidates(messages, candidates)

    ranked_ids = ranking_result.get("ranked_restaurant_ids", [])
    reasoning = ranking_result.get(
        "reasoning", "토론 내용을 바탕으로 순위를 선정했습니다."
    )

    # 순위 정보를 바탕으로 후보 식당 정렬
    # 랭킹에 있는 식당 우선, 나머지는 뒤로 (원래 순서 유지)
    id_to_rank = {rid: i for i, rid in enumerate(ranked_ids)}

    ranked_candidates = sorted(
        candidates, key=lambda c: id_to_rank.get(c.get("id"), float("inf"))
    )

    selection_message = AIMessage(
        content=f"""
        === 후보 식당 선호도 순위 ===
        
        {reasoning}
        
        [순위 결과]
        {_format_candidates(ranked_candidates)}
        
        상위 식당을 중심으로 실제 사용자 투표를 진행합니다.
        """,
        name="moderator",
    )

    return {
        "filtered_restaurants": ranked_candidates,
        "consensus_reached": True,
        "messages": [selection_message],
    }


def _format_candidates(candidates: List[Dict[str, Any]]) -> str:
    """후보 식당 목록을 포맷팅

    Args:
        candidates: 후보 식당 목록

    Returns:
        포맷팅된 문자열
    """
    if not candidates:
        return "없음"

    formatted = []
    for i, candidate in enumerate(candidates, 1):
        name = candidate.get("name", "Unknown")
        category = candidate.get("category", "N/A")
        location = candidate.get("location", "N/A")
        formatted.append(f"{i}. {name} (카테고리: {category}, 위치: {location})")

    return "\n".join(formatted)
