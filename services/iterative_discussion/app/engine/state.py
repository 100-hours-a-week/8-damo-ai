from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage


class ConsensusState(TypedDict):
    """협의 엔진 전용 State — shared/state 수정 없이 독립 운영"""

    # 입력
    user_ids: List[int]
    max_rounds: int
    user_data_list: List[Dict[str, Any]]
    dining_data: Dict[str, Any]
    filtered_restaurants: List[Dict[str, Any]]

    # Node 1 출력
    persona_prompts: Dict[str, str]

    # Node 2 출력
    candidate_pool: List[Dict[str, Any]]

    # Node 3 출력
    round: int
    messages: List[BaseMessage]
    dialogue_history: List[Dict[str, Any]]

    # Node 4 출력
    consensus_reached: bool
    consensus_candidates: List[Dict[str, Any]]

    # Node 5 출력
    persona_votes: List[Dict[str, Any]]
    final_selection: List[Dict[str, Any]]
    final_decision: str

    # 에러 처리
    is_error: bool
    error_message: str


def create_initial_state(
    user_ids: List[int],
    user_data_list: List[Dict[str, Any]],
    dining_data: Dict[str, Any],
    filtered_restaurants: List[Dict[str, Any]],
    max_rounds: int = 3,
) -> ConsensusState:
    """초기 상태를 생성하는 팩토리 함수"""
    return ConsensusState(
        user_ids=user_ids,
        max_rounds=max_rounds,
        user_data_list=user_data_list,
        dining_data=dining_data,
        filtered_restaurants=filtered_restaurants,
        persona_prompts={},
        candidate_pool=[],
        round=0,
        messages=[],
        dialogue_history=[],
        consensus_reached=False,
        consensus_candidates=[],
        persona_votes=[],
        final_selection=[],
        final_decision="",
        is_error=False,
        error_message="",
    )
