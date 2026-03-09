from langgraph.graph import END, StateGraph

from services.agent_dialogue.app.engine.state import AgentDialogueState
from services.agent_dialogue.app.nodes.moderator_preselect import moderator_preselect
from services.agent_dialogue.app.nodes.persona_factory import persona_factory
from services.agent_dialogue.app.nodes.restaurant_dialogue import restaurant_dialogue


def _check_error(state: AgentDialogueState) -> str:
    """에러 발생 시 즉시 END로 단축."""
    return "end" if state.get("is_error") else "continue"


def _after_restaurant_dialogue(state: AgentDialogueState) -> str:
    """restaurant_dialogue 완료 후 분기:
    - 에러 → END
    - 추천 5개 채움 → END
    - 현재 배치에 남은 식당 → 다음 식당 처리
    - 배치 완료 + 추가 ID 있음 → 다음 배치 fetch
    - 모두 소진 → END (fallback은 main.py에서 처리)
    """
    if state.get("is_error"):
        return "end"

    if len(state.get("recommended_restaurants", [])) >= 5:
        return "end"

    if state.get("restaurant_index", 0) < len(state.get("candidate_pool", [])):
        return "restaurant"

    offset = state.get("restaurant_offset", 0)
    total = len(state.get("filtered_restaurant_ids", []))
    if offset < total:
        return "preselect"

    return "end"


def build_agent_dialogue_graph() -> StateGraph:
    """3노드 그래프를 빌드하고 컴파일된 그래프를 반환."""
    graph = StateGraph(AgentDialogueState)

    # 노드 등록
    graph.add_node("persona_factory", persona_factory)
    graph.add_node("moderator_preselect", moderator_preselect)
    graph.add_node("restaurant_dialogue", restaurant_dialogue)

    # 엔트리
    graph.set_entry_point("persona_factory")

    # persona_factory → 에러 체크 → moderator_preselect
    graph.add_conditional_edges(
        "persona_factory",
        _check_error,
        {"continue": "moderator_preselect", "end": END},
    )

    # moderator_preselect → 에러 체크 → restaurant_dialogue
    graph.add_conditional_edges(
        "moderator_preselect",
        _check_error,
        {"continue": "restaurant_dialogue", "end": END},
    )

    # restaurant_dialogue → 조건부 분기
    graph.add_conditional_edges(
        "restaurant_dialogue",
        _after_restaurant_dialogue,
        {
            "restaurant": "restaurant_dialogue",  # 현재 배치 다음 식당
            "preselect": "moderator_preselect",   # 다음 배치 fetch
            "end": END,
        },
    )

    return graph.compile()
