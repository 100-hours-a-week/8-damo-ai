"""멀티에이전트 토론 시스템 LangGraph 워크플로우

MULTI_AGENT_DESIGN_DOC.md를 기반으로 구현된 LangGraph 워크플로우입니다.

워크플로우:
1. initialize_state: 상태 초기화
2. topic_proposal: 주제/후보 발제
3. agent_discussion: 에이전트 토론 (Round-Robin)
4. summarize: 중간 요약
5. vote: 투표 및 선호도 조사
6. check_consensus: 합의 도달 확인
   - consensus -> final_select: 최종 선정
   - no_consensus -> topic_proposal: 다음 라운드
   - force_resolve -> force_resolve: 강제 해결
"""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END

from .states.discussion_state import DiscussionState
from .nodes import (
    initialize_state_node,
    topic_proposal_node,
    agent_discussion_node,
    summarize_node,
    vote_node,
    final_select_node,
    force_resolve_node,
)
from .edges.conditions import check_consensus


async def create_discussion_graph(
    user_ids: List[int],
    candidate_restaurants: List[Dict[str, Any]],
    max_rounds: int = 3,
):
    """멀티에이전트 토론 그래프를 생성하고 실행합니다.

    Args:
        user_ids: 참여 사용자 ID 목록
        candidate_restaurants: 후보 식당 목록
        max_rounds: 최대 라운드 수 (기본값: 3)

    Returns:
        최종 상태 (final_decision, discussion_log 포함)
    """
    # StateGraph 생성
    builder = StateGraph(DiscussionState)

    # 노드 추가
    builder.add_node("initialize_state", initialize_state_node)
    builder.add_node("topic_proposal", topic_proposal_node)
    builder.add_node("agent_discussion", agent_discussion_node)
    builder.add_node("summarize", summarize_node)
    builder.add_node("vote", vote_node)
    builder.add_node("final_select", final_select_node)
    builder.add_node("force_resolve", force_resolve_node)

    # 엣지 연결
    builder.add_edge(START, "initialize_state")
    builder.add_edge("initialize_state", "topic_proposal")
    builder.add_edge("topic_proposal", "agent_discussion")
    builder.add_edge("agent_discussion", "summarize")
    builder.add_edge("summarize", "vote")

    # 조건부 엣지: 합의 확인
    builder.add_conditional_edges(
        "vote",
        check_consensus,
        {
            "consensus": "final_select",
            "no_consensus": "topic_proposal",
            "force_resolve": "force_resolve",
        },
    )

    # 최종 노드에서 종료
    builder.add_edge("final_select", END)
    builder.add_edge("force_resolve", END)

    # 그래프 컴파일
    graph = builder.compile()

    # 초기 상태 설정
    initial_state: DiscussionState = {
        "round": 0,  # initialize_state_node에서 1로 설정됨
        "messages": [],
        "candidates": candidate_restaurants,
        "votes": {},
        "consensus_reached": False,
        "final_decision": None,
        "user_ids": user_ids,
        "max_rounds": max_rounds,
    }

    # 그래프 실행
    final_state = await graph.ainvoke(initial_state)

    return final_state


async def run_iterative_discussion(
    user_ids: List[int], candidate_restaurant_ids: List[str], max_rounds: int = 3
) -> Dict[str, Any]:
    """멀티에이전트 토론을 실행하는 메인 함수

    API 엔드포인트에서 호출될 함수입니다.

    Args:
        user_ids: 참여 사용자 ID 목록
        candidate_restaurant_ids: 후보 식당 ID 목록
        max_rounds: 최대 라운드 수

    Returns:
        토론 결과 (discussion_log, final_decision, reasoning)
    """
    # TODO: MongoDB에서 실제 식당 정보 조회
    # 현재는 Mock 데이터 사용
    candidate_restaurants = [
        {
            "id": restaurant_id,
            "name": f"Restaurant {restaurant_id}",
            "category": "Korean",
            "location": "Seoul",
        }
        for restaurant_id in candidate_restaurant_ids
    ]

    # 그래프 실행
    final_state = await create_discussion_graph(
        user_ids=user_ids,
        candidate_restaurants=candidate_restaurants,
        max_rounds=max_rounds,
    )

    # 결과 포맷팅
    discussion_log = [
        {"speaker": getattr(msg, "name", "system"), "message": msg.content}
        for msg in final_state.get("messages", [])
    ]

    # 투표 결과 분석
    votes = final_state.get("votes", {})
    from collections import Counter

    vote_counts = Counter(votes.values())

    reasoning = (
        "합의에 도달하여 선정됨"
        if final_state.get("consensus_reached")
        else "다수결로 선정됨"
    )
    if vote_counts:
        top_restaurant, count = vote_counts.most_common(1)[0]
        reasoning += f" ({count}/{len(votes)}표)"

    return {
        "discussion_log": discussion_log,
        "final_decision": final_state.get("final_decision"),
        "reasoning": reasoning,
        "consensus_reached": final_state.get("consensus_reached", False),
        "total_rounds": final_state.get("round", 0),
    }
