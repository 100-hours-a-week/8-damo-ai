from typing import Any, Dict, List, TypedDict


class AgentDialogueState(TypedDict):
    """agent_dialogue 엔진 전용 State"""

    # ── 입력 ───────────────────────────────────────────────────────────────
    user_ids: List[int]
    user_data_list: List[Dict[str, Any]]
    dining_data: Dict[str, Any]
    filtered_restaurant_ids: List[str]      # 전체 후보 ID 목록 (외부 입력)
    vote_result_list: List[Dict[str, Any]]  # 재추천 시 thumbup/thumbdown

    # ── Node 1: persona_factory ────────────────────────────────────────────
    persona_prompts: Dict[str, str]         # user_id → system prompt

    # ── Node 2: moderator_preselect ────────────────────────────────────────
    candidate_pool: List[Dict[str, Any]]    # 현재 배치 식당 (최대 5개, score 포함)
    restaurant_offset: int                  # filtered_restaurant_ids 다음 fetch 시작 위치

    # ── Node 3: restaurant_dialogue ────────────────────────────────────────
    restaurant_index: int                   # 현재 배치 내 처리 중인 인덱스 (0 ~ batch_size-1)
    dialogue_history: List[Dict[str, Any]]  # 전체 대화 기록 (분석가 + 반응 + 투표)
    recommended_restaurants: List[Dict[str, Any]]  # 과반수 통과 식당 (최대 5개)
    processed_restaurants: List[Dict[str, Any]]    # 투표 완료된 모든 식당 (fallback용)

    # ── 최종 출력 ──────────────────────────────────────────────────────────
    final_selection: List[Dict[str, Any]]   # 최종 Top 5
    persona_votes: List[Dict[str, Any]]     # 전체 투표 기록 (self_evolution 저장용)

    # ── 에러 처리 ──────────────────────────────────────────────────────────
    is_error: bool
    error_message: str


def create_initial_state(
    user_ids: List[int],
    dining_data: Dict[str, Any],
    filtered_restaurant_ids: List[str],
    vote_result_list: List[Dict[str, Any]] | None = None,
) -> AgentDialogueState:
    """초기 상태를 생성하는 팩토리 함수."""
    return AgentDialogueState(
        user_ids=user_ids,
        user_data_list=[],
        dining_data=dining_data,
        filtered_restaurant_ids=filtered_restaurant_ids,
        vote_result_list=vote_result_list or [],
        persona_prompts={},
        candidate_pool=[],
        restaurant_offset=0,
        restaurant_index=0,
        dialogue_history=[],
        recommended_restaurants=[],
        processed_restaurants=[],
        final_selection=[],
        persona_votes=[],
        is_error=False,
        error_message="",
    )
