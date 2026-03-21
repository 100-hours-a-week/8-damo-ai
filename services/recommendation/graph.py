"""Pipeline graph: recommendation + agent_dialogue + rag_reason 통합 그래프 (평탄화).

흐름:
  START → [branch] → fetch_nearby_restaurants | validate_user_group
        → score_by_budget → apply_allergy_penalty
        → rerank_by_semantic_score → initialize_dialogue_state
        → create_group_personas → select_candidate_batch → run_persona_discussion(loop)
        → apply_dialogue_fallback → persist_voting_records → persist_dialogue_history
        → generate_recommendation_reasons → END
"""

import logging
from typing import Optional

from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph, START, END

# recommend 서브그래프 노드 함수
from services.recommendation.sub_graphs.recommend import distance_node, budget_node

# refresh 서브그래프 노드 함수
from services.recommendation.sub_graphs.refresh import (
    is_user_group_valid,
    is_remaining_candidate,
)

# allergy 서브그래프 노드 함수
from services.recommendation.sub_graphs.allergy import allergy_node

from services.recommendation.semantic_rerank_node import semantic_rerank_node

# 브릿지 + 저장 노드
from services.recommendation.bridge_node import bridge_node
from services.recommendation.save_votes_node import save_votes_node
from services.recommendation.save_dialogue_node import save_dialogue_node
from services.recommendation.rag_reason_node import rag_reason_node

# agent_dialogue 노드 (개별 import)
from services.agent_dialogue.app.nodes.persona_factory import persona_factory
from services.agent_dialogue.app.nodes.moderator_preselect import moderator_preselect
from services.agent_dialogue.app.nodes.restaurant_dialogue import restaurant_dialogue
from services.agent_dialogue.app.nodes.score_fallback import score_fallback

from services.recommendation.state import PipelineState

logger = logging.getLogger(__name__)


# ── 분기 함수 ─────────────────────────────────────────────────────────────────


def _branch_initial_or_refresh(state: PipelineState) -> str:
    """is_initial_workflow 기준으로 fetch_nearby_restaurants / validate_user_group 분기."""
    branch = (
        "fetch_nearby_restaurants"
        if state.get("is_initial_workflow", True)
        else "validate_user_group"
    )
    logger.info("[GRAPH] 분기 선택: %s", branch)
    return branch


def _check_error(state: PipelineState) -> str:
    """에러 발생 시 END로 단축."""
    if state.get("is_error"):
        logger.warning("[GRAPH] 에러 감지 → END: %s", state.get("error_message"))
        return "end"
    return "continue"


def _check_error_or_rescue(state: PipelineState) -> str:
    """에러 발생 시 rescue_from_error로 구제 (식당 데이터가 있는 구간 전용)."""
    if state.get("is_error"):
        logger.warning(
            "[GRAPH] 에러 감지 → rescue_from_error: %s", state.get("error_message")
        )
        return "rescue"
    return "continue"


def _rescue_from_error(state: PipelineState) -> dict:
    """에러 구제 노드: filtered_restaurant → processed_restaurants 변환 후 score_fallback 진입 준비.

    - filtered_restaurant의 final_score(또는 total_score)를 processed_restaurants 형식으로 변환
    - filtered_restaurant_ids가 미설정일 경우 함께 생성 (initialize_dialogue_state 이전 에러 시 대비)
    - is_error 초기화 → apply_dialogue_fallback이 정상 실행되도록 보장
    """
    filtered = state.get("filtered_restaurant", [])
    logger.warning(
        "[GRAPH] rescue_from_error: filtered_restaurant=%d개로 score 기반 추천 진행",
        len(filtered),
    )

    processed = [
        {
            "restaurant_id": str(r.get("_id")),
            "place_name": r.get("place_name", ""),
            "score": r.get("final_score", r.get("total_score", 0.0)),
        }
        for r in filtered
        if r.get("_id")
    ]

    ids = [str(r.get("_id")) for r in filtered if r.get("_id")]

    return {
        "is_error": False,
        "processed_restaurants": processed,
        "filtered_restaurant_ids": ids,
        # score_fallback이 읽는 recommended_restaurants는 건드리지 않음 (기존 값 유지)
    }


def _route_after_validate_user_group(state: PipelineState) -> str:
    """validate_user_group 완료 후 3방향 분기."""
    if state.get("is_error"):
        return "end"
    if state.get("is_group_changed", False):
        return "fetch"
    return "load"


def _route_after_load_remaining(state: PipelineState) -> str:
    """load_remaining_candidates 완료 후 분기: DB 소진 시 신규 추천 경로."""
    if state.get("no_db_candidates", False):
        return "fetch"
    return "continue"


def _after_restaurant_dialogue(state: PipelineState) -> str:
    """run_persona_discussion 완료 후 분기:
    - 에러 → apply_dialogue_fallback (안전하게 마무리)
    - 추천 5개 채움 → apply_dialogue_fallback (정상 종료 경로)
    - 현재 배치에 남은 식당 → 다음 식당 처리
    - 배치 완료 + 추가 ID 있음 → 다음 배치 fetch
    - 모두 소진 → apply_dialogue_fallback
    """
    if state.get("is_error"):
        logger.warning("[GRAPH] run_persona_discussion 에러 → apply_dialogue_fallback")
        return "fallback"

    if len(state.get("recommended_restaurants", [])) >= 5:
        logger.info("[GRAPH] 추천 5개 달성 → apply_dialogue_fallback")
        return "fallback"

    if state.get("restaurant_index", 0) < len(state.get("candidate_pool", [])):
        return "restaurant"

    offset = state.get("restaurant_offset", 0)
    total = len(state.get("filtered_restaurant_ids", []))
    if offset < total:
        return "preselect"

    logger.info("[GRAPH] 모든 후보 소진 → apply_dialogue_fallback")
    return "fallback"


# ── 그래프 빌더 ───────────────────────────────────────────────────────────────


def build_pipeline_graph(
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> Runnable:
    """통합 파이프라인 그래프를 빌드하고 컴파일된 그래프를 반환.

    Args:
        checkpointer: LangGraph 체크포인터. 설정 시 노드 실행마다 상태를 저장하며
                      프로세스 재시작 시 thread_id(=dining_id)를 기준으로 중단 지점부터 재개한다.
    """
    workflow = StateGraph(PipelineState)

    # recommend 경로 노드
    workflow.add_node("fetch_nearby_restaurants", distance_node)
    workflow.add_node("score_by_budget", budget_node)

    # refresh 경로 노드
    workflow.add_node("validate_user_group", is_user_group_valid)
    workflow.add_node("load_remaining_candidates", is_remaining_candidate)

    # 공통 필터링 노드
    workflow.add_node("apply_allergy_penalty", allergy_node)
    workflow.add_node("rerank_by_semantic_score", semantic_rerank_node)

    # 브릿지 노드
    workflow.add_node("initialize_dialogue_state", bridge_node)

    # agent_dialogue 노드
    workflow.add_node("create_group_personas", persona_factory)
    workflow.add_node("select_candidate_batch", moderator_preselect)
    workflow.add_node("run_persona_discussion", restaurant_dialogue)
    workflow.add_node("apply_dialogue_fallback", score_fallback)

    # 저장 + RAG 노드
    workflow.add_node("persist_voting_records", save_votes_node)
    workflow.add_node("persist_dialogue_history", save_dialogue_node)
    workflow.add_node("generate_recommendation_reasons", rag_reason_node)

    # 에러 구제 노드
    workflow.add_node("rescue_from_error", _rescue_from_error)

    # ── 엣지 ──────────────────────────────────────────────────────────────────

    # START → fetch_nearby_restaurants 또는 validate_user_group
    workflow.add_conditional_edges(
        START,
        _branch_initial_or_refresh,
        {
            "fetch_nearby_restaurants": "fetch_nearby_restaurants",
            "validate_user_group": "validate_user_group",
        },
    )

    # fetch_nearby_restaurants → score_by_budget (에러 시 END)
    workflow.add_conditional_edges(
        "fetch_nearby_restaurants",
        _check_error,
        {"continue": "score_by_budget", "end": END},
    )

    # validate_user_group → 3방향 분기
    workflow.add_conditional_edges(
        "validate_user_group",
        _route_after_validate_user_group,
        {
            "end": END,
            "fetch": "fetch_nearby_restaurants",
            "load": "load_remaining_candidates",
        },
    )

    # load_remaining_candidates → apply_allergy_penalty (성공) 또는 fetch_nearby_restaurants (DB 소진)
    workflow.add_conditional_edges(
        "load_remaining_candidates",
        _route_after_load_remaining,
        {
            "fetch": "fetch_nearby_restaurants",
            "continue": "apply_allergy_penalty",
        },
    )

    # score_by_budget → apply_allergy_penalty
    workflow.add_edge("score_by_budget", "apply_allergy_penalty")

    # apply_allergy_penalty → 에러 시 rescue_from_error, 정상 시 rerank_by_semantic_score
    workflow.add_conditional_edges(
        "apply_allergy_penalty",
        _check_error_or_rescue,
        {"continue": "rerank_by_semantic_score", "rescue": "rescue_from_error"},
    )

    # rerank_by_semantic_score: 내부에서 에러를 자체 처리하므로 단순 직결
    workflow.add_edge("rerank_by_semantic_score", "initialize_dialogue_state")

    # initialize_dialogue_state → 에러 시 rescue_from_error, 정상 시 create_group_personas
    workflow.add_conditional_edges(
        "initialize_dialogue_state",
        _check_error_or_rescue,
        {"continue": "create_group_personas", "rescue": "rescue_from_error"},
    )

    # create_group_personas → 에러 시 rescue_from_error, 정상 시 select_candidate_batch
    workflow.add_conditional_edges(
        "create_group_personas",
        _check_error_or_rescue,
        {"continue": "select_candidate_batch", "rescue": "rescue_from_error"},
    )

    # select_candidate_batch → 에러 시 rescue_from_error, 정상 시 run_persona_discussion
    workflow.add_conditional_edges(
        "select_candidate_batch",
        _check_error_or_rescue,
        {"continue": "run_persona_discussion", "rescue": "rescue_from_error"},
    )

    # rescue_from_error → apply_dialogue_fallback (score_fallback)
    workflow.add_edge("rescue_from_error", "apply_dialogue_fallback")

    # run_persona_discussion → 조건부 분기 (loop / preselect / fallback)
    workflow.add_conditional_edges(
        "run_persona_discussion",
        _after_restaurant_dialogue,
        {
            "restaurant": "run_persona_discussion",
            "preselect": "select_candidate_batch",
            "fallback": "apply_dialogue_fallback",
        },
    )

    # apply_dialogue_fallback → persist_voting_records → persist_dialogue_history → generate_recommendation_reasons → END
    workflow.add_edge("apply_dialogue_fallback", "persist_voting_records")
    workflow.add_edge("persist_voting_records", "persist_dialogue_history")
    workflow.add_edge("persist_dialogue_history", "generate_recommendation_reasons")
    workflow.add_edge("generate_recommendation_reasons", END)

    return workflow.compile(checkpointer=checkpointer)
