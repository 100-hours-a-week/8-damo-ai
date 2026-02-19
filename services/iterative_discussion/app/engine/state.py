from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage

from services.iterative_discussion.app.utils.monitoring import init_consensus_trace


class ConsensusState(TypedDict):
    """협의 엔진 전용 State — shared/state 수정 없이 독립 운영"""

    # 입력
    user_ids: List[int]
    max_rounds: int
    user_data_list: List[Dict[str, Any]]
    dining_data: Dict[str, Any]
    filtered_restaurant_ids: List[str]
    vote_result_list: List[Dict[str, Any]]  # 재추천 시 thumbup/thumbdown (없으면 빈 리스트)

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

    # 모니터링
    langfuse_trace_id: str

    # 에러 처리
    is_error: bool
    error_message: str


def create_initial_state(
    user_ids: List[int],
    dining_data: Dict[str, Any],
    filtered_restaurant_ids: List[str],
    max_rounds: int = 3,
    vote_result_list: List[Dict[str, Any]] | None = None,
) -> ConsensusState:
    """초기 상태를 생성하는 팩토리 함수.

    user_data_list는 Node 1(persona_factory)에서 DB 조회 후 채워진다.
    식당 전체 문서는 Node 2(moderator_preselect)에서 DB 조회한다.
    """
    session_id = str(dining_data.get("diningId") or dining_data.get("dining_id") or "")
    trace_id = init_consensus_trace(
        session_id=session_id,
        metadata={"user_ids": user_ids, "max_rounds": max_rounds},
    )

    return ConsensusState(
        user_ids=user_ids,
        max_rounds=max_rounds,
        user_data_list=[],
        dining_data=dining_data,
        filtered_restaurant_ids=filtered_restaurant_ids,
        vote_result_list=vote_result_list or [],
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
        langfuse_trace_id=trace_id,
        is_error=False,
        error_message="",
    )
