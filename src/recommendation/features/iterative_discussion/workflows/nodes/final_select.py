"""최종 추천 식당 5개 선정 노드"""

from typing import Dict, Any, List
from collections import Counter
from langchain_core.messages import AIMessage


async def final_select_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """토론 후 최종 추천할 식당 5개를 선정하는 노드

    토론 내용에서 언급된 식당들의 빈도를 분석하여
    상위 5개를 최종 후보로 선정합니다.

    Args:
        state: 현재 상태

    Returns:
        final_candidates (5개)가 업데이트된 상태
    """
    candidates = state.get("candidates", [])
    messages = state.get("messages", [])

    # 후보가 5개 이하면 그대로 사용
    if len(candidates) <= 5:
        final_candidates = candidates
        selection_message = AIMessage(
            content=f"""
            === 최종 추천 식당 선정 ===
            
            후보 식당이 {len(candidates)}개이므로 모두 최종 추천 대상입니다.
            
            최종 추천 식당:
            {_format_candidates(final_candidates)}
            
            이제 실제 사용자 투표를 진행합니다.
            """,
            name="moderator",
        )
    else:
        # 토론 내용에서 각 식당 언급 빈도 분석
        restaurant_mentions = _analyze_mentions(candidates, messages)

        # 상위 5개 선정
        top_5 = restaurant_mentions.most_common(5)
        final_candidates = [
            next(c for c in candidates if c.get("id") == rest_id)
            for rest_id, _ in top_5
        ]

        selection_message = AIMessage(
            content=f"""
            === 최종 추천 식당 선정 ===
            
            토론 내용을 분석하여 가장 많이 언급된 상위 5개 식당을 선정했습니다.
            
            최종 추천 식당:
            {_format_candidates(final_candidates)}
            
            이제 실제 사용자 투표를 진행합니다.
            """,
            name="moderator",
        )

    return {
        "final_candidates": final_candidates,
        "consensus_reached": True,
        "messages": [selection_message],
    }


def _analyze_mentions(candidates: List[Dict[str, Any]], messages: List[Any]) -> Counter:
    """토론 메시지에서 각 식당의 언급 빈도 분석

    Args:
        candidates: 후보 식당 목록
        messages: 토론 메시지 목록

    Returns:
        Counter: {restaurant_id: mention_count}
    """
    mentions = Counter()

    # 에이전트 메시지만 추출
    agent_messages = [
        msg
        for msg in messages
        if hasattr(msg, "name") and msg.name and msg.name.startswith("agent_")
    ]

    # 각 식당 이름/ID가 메시지에 언급되었는지 확인
    for candidate in candidates:
        rest_id = candidate.get("id", "")
        rest_name = candidate.get("name", "")

        for msg in agent_messages:
            content = msg.content.lower()
            # 이름이나 ID가 언급되면 카운트
            if rest_name.lower() in content or rest_id.lower() in content:
                mentions[rest_id] += 1

    # 언급이 없는 식당은 0으로 초기화
    for candidate in candidates:
        rest_id = candidate.get("id", "")
        if rest_id not in mentions:
            mentions[rest_id] = 0

    return mentions


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
