from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage


class ConsensusState(TypedDict):
    """협의 엔진 전용 State — shared/state 수정 없이 독립 운영"""

    # ── 입력 ──────────────────────────────────────────────────────────────────
    user_ids: List[int]                  # 토론 참여 유저 ID 목록
    max_rounds: int                      # 최대 토론 라운드 수
    min_rounds: int                      # 합의 판정 시작 전 보장되는 최소 라운드 수
    rotations_per_round: int             # 한 라운드에서 페르소나별 발언 반복 횟수
    user_data_list: List[Dict[str, Any]] # 유저 프로필 (Node 1에서 DB 조회 후 채워짐)
    dining_data: Dict[str, Any]          # 회식 정보 (예산, 날짜 등)
    filtered_restaurant_ids: List[str]   # 외부에서 전달된 초기 식당 ID 목록 (필터링 전)
    vote_result_list: List[Dict[str, Any]]  # (미사용) 재추천 시 thumbup/thumbdown 결과

    # ── Node 1: persona_factory 출력 ──────────────────────────────────────────
    persona_prompts: Dict[str, str]      # user_id → 페르소나 system prompt

    # ── Node 2: moderator_preselect 출력 ─────────────────────────────────────
    candidate_pool: List[Dict[str, Any]] # 점수 기반 Top 10 선별된 식당 문서 목록

    # ── Node 2.5: restaurant_summarizer 출력 ─────────────────────────────────
    candidate_summaries: Dict[str, str]  # restaurant _id → 자연어 요약 (실패 식당은 생략)

    # ── Node 3: multi_agent_dialogue 출력 ────────────────────────────────────
    round: int                           # 현재까지 완료된 라운드 수
    messages: List[BaseMessage]          # LangChain 메시지 히스토리 (LLM 컨텍스트용)
    dialogue_history: List[Dict[str, Any]]  # 전체 발언 기록 (user_id, nickname, round, content)

    # ── Node 4: consensus_assessment 출력 ────────────────────────────────────
    consensus_reached: bool              # 합의 도달 여부
    consensus_candidates: List[Dict[str, Any]]  # 합의된 식당 후보 목록
    rejected_restaurant_ids: List[str]   # 토론에서 부정적으로 언급되어 제외할 식당 ID 목록
    moderator_feedback: str              # 합의 미달 시 다음 라운드에 주입되는 사회자 가이드

    # ── Node 5: persona_voting 출력 ──────────────────────────────────────────
    persona_votes: List[Dict[str, Any]]  # 페르소나별 최종 투표 결과
    final_selection: List[Dict[str, Any]]  # 최종 선정된 식당 목록
    final_decision: str                  # 최종 결정 요약 텍스트

    # ── 에러 처리 ─────────────────────────────────────────────────────────────
    is_error: bool                       # 에러 발생 여부
    error_message: str                   # 에러 메시지


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
