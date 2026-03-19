"""Pipeline graph: recommendation + agent_dialogue + rag_reason 통합 그래프.

흐름:
  START → [branch] → recommend_sg | refresh_sg
        → bridge
        → persona_factory → moderator_preselect → restaurant_dialogue(loop)
        → score_fallback → save_votes_node → save_dialogue_node → rag_reason_node
        → END
"""
import logging

from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph, START, END

# 서브그래프
from services.recommendation.sub_graphs.recommend import get_recommend_graph
from services.recommendation.sub_graphs.refresh import get_refresh_graph

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
    """is_initial_workflow 기준으로 recommend_sg / refresh_sg 분기."""
    branch = "recommend" if state.get("is_initial_workflow", True) else "refresh"
    logger.info("[GRAPH] 분기 선택: %s", branch)
    return branch


def _check_error(state: PipelineState) -> str:
    """에러 발생 시 END로 단축."""
    if state.get("is_error"):
        logger.warning("[GRAPH] 에러 감지 → END: %s", state.get("error_message"))
        return "end"
    return "continue"


def _after_restaurant_dialogue(state: PipelineState) -> str:
    """restaurant_dialogue 완료 후 분기:
    - 에러 → score_fallback (안전하게 마무리)
    - 추천 5개 채움 → score_fallback (정상 종료 경로)
    - 현재 배치에 남은 식당 → 다음 식당 처리
    - 배치 완료 + 추가 ID 있음 → 다음 배치 fetch
    - 모두 소진 → score_fallback
    """
    if state.get("is_error"):
        logger.warning("[GRAPH] restaurant_dialogue 에러 → score_fallback")
        return "fallback"

    if len(state.get("recommended_restaurants", [])) >= 5:
        logger.info("[GRAPH] 추천 5개 달성 → score_fallback")
        return "fallback"

    if state.get("restaurant_index", 0) < len(state.get("candidate_pool", [])):
        return "restaurant"

    offset = state.get("restaurant_offset", 0)
    total = len(state.get("filtered_restaurant_ids", []))
    if offset < total:
        return "preselect"

    logger.info("[GRAPH] 모든 후보 소진 → score_fallback")
    return "fallback"


# ── 그래프 빌더 ───────────────────────────────────────────────────────────────

def build_pipeline_graph() -> Runnable:
    """통합 파이프라인 그래프를 빌드하고 컴파일된 그래프를 반환."""
    workflow = StateGraph(PipelineState)

    # 서브그래프 노드 등록
    workflow.add_node("recommend", get_recommend_graph())
    workflow.add_node("refresh", get_refresh_graph())

    # 브릿지 노드
    workflow.add_node("bridge", bridge_node)

    # agent_dialogue 노드
    workflow.add_node("persona_factory", persona_factory)
    workflow.add_node("moderator_preselect", moderator_preselect)
    workflow.add_node("restaurant_dialogue", restaurant_dialogue)
    workflow.add_node("score_fallback", score_fallback)

    # 저장 + RAG 노드
    workflow.add_node("save_votes_node", save_votes_node)
    workflow.add_node("save_dialogue_node", save_dialogue_node)
    workflow.add_node("rag_reason_node", rag_reason_node)

    # ── 엣지 ──────────────────────────────────────────────────────────────────

    # START → recommend_sg 또는 refresh_sg
    workflow.add_conditional_edges(
        START,
        _branch_initial_or_refresh,
        {"recommend": "recommend", "refresh": "refresh"},
    )

    # 양쪽 모두 bridge로 수렴
    workflow.add_edge("recommend", "bridge")
    workflow.add_edge("refresh", "bridge")

    # bridge → persona_factory (에러 체크)
    workflow.add_conditional_edges(
        "bridge",
        _check_error,
        {"continue": "persona_factory", "end": END},
    )

    # persona_factory → 에러 체크 → moderator_preselect
    workflow.add_conditional_edges(
        "persona_factory",
        _check_error,
        {"continue": "moderator_preselect", "end": END},
    )

    # moderator_preselect → 에러 체크 → restaurant_dialogue
    workflow.add_conditional_edges(
        "moderator_preselect",
        _check_error,
        {"continue": "restaurant_dialogue", "end": END},
    )

    # restaurant_dialogue → 조건부 분기 (loop / preselect / fallback)
    workflow.add_conditional_edges(
        "restaurant_dialogue",
        _after_restaurant_dialogue,
        {
            "restaurant": "restaurant_dialogue",
            "preselect": "moderator_preselect",
            "fallback": "score_fallback",
        },
    )

    # score_fallback → save_votes → save_dialogue → rag_reason → END
    workflow.add_edge("score_fallback", "save_votes_node")
    workflow.add_edge("save_votes_node", "save_dialogue_node")
    workflow.add_edge("save_dialogue_node", "rag_reason_node")
    workflow.add_edge("rag_reason_node", END)

    return workflow.compile()
