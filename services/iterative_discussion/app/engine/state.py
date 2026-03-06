from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage


class ConsensusState(TypedDict):
    """협의 엔진 전용 State — shared/state 수정 없이 독립 운영"""

    # 입력
    user_ids: List[int]
    max_rounds: int
    min_rounds: int  # 최소 토론 라운드 수
    rotations_per_round: int  # 라운드 내 페르소나 발언 횟수
    user_data_list: List[Dict[str, Any]]
    dining_data: Dict[str, Any]
    filtered_restaurant_ids: List[str]
    vote_result_list: List[
        Dict[str, Any]
    ]  # (미사용 — 진화 로직 외부 이관) 재추천 시 thumbup/thumbdown

    # Node 1 출력
    persona_prompts: Dict[str, str]

    # Node 2 출력
    candidate_pool: List[Dict[str, Any]]

    # Node 2.5 출력 (restaurant_summarizer)
    candidate_summaries: Dict[str, str]  # restaurant _id(str) → 자연어 요약

    # Node 3 출력
    round: int
    messages: List[BaseMessage]
    dialogue_history: List[Dict[str, Any]]

    # Node 4 출력
    consensus_reached: bool
    consensus_candidates: List[Dict[str, Any]]
    rejected_restaurant_ids: List[str]  # 토론에서 부정적으로 언급된 식당 ID
    moderator_feedback: str  # 합의 미달 시 다음 라운드 가이드 메시지

    # Node 5 출력
    persona_votes: List[Dict[str, Any]]
    final_selection: List[Dict[str, Any]]
    final_decision: str

    # 에러 처리
    is_error: bool
    error_message: str


def create_initial_state(
    user_ids: List[int],
    dining_data: Dict[str, Any],
    filtered_restaurant_ids: List[str],
    max_rounds: int = 5,
    min_rounds: int = 2,
    rotations_per_round: int = 2,
    vote_result_list: List[Dict[str, Any]] | None = None,
) -> ConsensusState:
    """초기 상태를 생성하는 팩토리 함수.

    user_data_list는 Node 1(persona_factory)에서 DB 조회 후 채워진다.
    식당 전체 문서는 Node 2(moderator_preselect)에서 DB 조회한다.
    """
    # min_rounds가 max_rounds 이상이면 합의 판정 기회가 0이 됨 — 방어
    min_rounds = min(min_rounds, max_rounds - 1)

    return ConsensusState(
        user_ids=user_ids,
        max_rounds=max_rounds,
        min_rounds=min_rounds,
        rotations_per_round=rotations_per_round,
        user_data_list=[],
        dining_data=dining_data,
        filtered_restaurant_ids=filtered_restaurant_ids,
        vote_result_list=vote_result_list or [],
        persona_prompts={},
        candidate_pool=[],
        candidate_summaries={},
        round=0,
        messages=[],
        dialogue_history=[],
        consensus_reached=False,
        consensus_candidates=[],
        rejected_restaurant_ids=[],
        moderator_feedback="",
        persona_votes=[],
        final_selection=[],
        final_decision="",
        is_error=False,
        error_message="",
    )
