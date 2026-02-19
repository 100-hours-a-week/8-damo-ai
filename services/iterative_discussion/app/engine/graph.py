from langgraph.graph import END, StateGraph

from services.iterative_discussion.app.engine.state import ConsensusState
from services.iterative_discussion.app.nodes.consensus_assessment import consensus_assessment
from services.iterative_discussion.app.nodes.moderator_preselect import moderator_preselect
from services.iterative_discussion.app.nodes.multi_agent_dialogue import multi_agent_dialogue
from services.iterative_discussion.app.nodes.persona_factory import persona_factory
from services.iterative_discussion.app.nodes.persona_voting import persona_voting
from services.iterative_discussion.app.nodes.self_evolution import self_evolution


def _after_persona_factory(state: ConsensusState) -> str:
    """Node 1 이후 조건부 엣지: 재추천(vote_data 있음) → 진화, 첫 추천 → 바로 필터링."""
    if state.get("is_error"):
        return "end"
    if state.get("vote_result_list"):
        return "evolve"
    return "preselect"


def _check_error(state: ConsensusState) -> str:
    """에러 발생 시 즉시 END로 단축."""
    if state.get("is_error"):
        return "end"
    return "continue"


def _should_continue(state: ConsensusState) -> str:
    """Node 4 이후 조건부 엣지: 루프백 or 투표 진행."""
    if state.get("is_error"):
        return "end"
    if state.get("consensus_reached") or state.get("round", 0) >= state.get("max_rounds", 3):
        return "vote"
    return "dialogue"


def build_consensus_graph() -> StateGraph:
    """6노드 flat graph를 빌드하고 컴파일된 그래프를 반환."""
    graph = StateGraph(ConsensusState)

    # 노드 등록
    graph.add_node("persona_factory", persona_factory)
    graph.add_node("self_evolution", self_evolution)
    graph.add_node("moderator_preselect", moderator_preselect)
    graph.add_node("multi_agent_dialogue", multi_agent_dialogue)
    graph.add_node("consensus_assessment", consensus_assessment)
    graph.add_node("persona_voting", persona_voting)

    # 엔트리
    graph.set_entry_point("persona_factory")

    # Node 1 → 조건부: 재추천이면 self_evolution, 아니면 moderator_preselect
    graph.add_conditional_edges(
        "persona_factory",
        _after_persona_factory,
        {
            "evolve": "self_evolution",
            "preselect": "moderator_preselect",
            "end": END,
        },
    )

    # self_evolution → 에러 체크 → moderator_preselect
    graph.add_conditional_edges(
        "self_evolution",
        _check_error,
        {"continue": "moderator_preselect", "end": END},
    )

    # moderator_preselect → 에러 체크 → multi_agent_dialogue
    graph.add_conditional_edges(
        "moderator_preselect",
        _check_error,
        {"continue": "multi_agent_dialogue", "end": END},
    )

    # multi_agent_dialogue → 에러 체크 → consensus_assessment
    graph.add_conditional_edges(
        "multi_agent_dialogue",
        _check_error,
        {"continue": "consensus_assessment", "end": END},
    )

    # Node 4 → 조건부: 루프백 or Node 5
    graph.add_conditional_edges(
        "consensus_assessment",
        _should_continue,
        {
            "dialogue": "multi_agent_dialogue",
            "vote": "persona_voting",
            "end": END,
        },
    )

    graph.add_edge("persona_voting", END)

    return graph.compile()
