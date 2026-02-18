from langgraph.graph import END, StateGraph

from services.iterative_discussion.app.engine.state import ConsensusState


def _stub_node(state: ConsensusState) -> dict:
    """Phase 2~4에서 실제 구현으로 교체될 pass-through stub."""
    return {}


def _should_continue(state: ConsensusState) -> str:
    """Node 4 이후 조건부 엣지: 루프백 or 투표 진행."""
    if state.get("is_error"):
        return "end"
    if state.get("consensus_reached") or state.get("round", 0) >= state.get("max_rounds", 3):
        return "vote"
    return "dialogue"


def build_consensus_graph() -> StateGraph:
    """5노드 flat graph를 빌드하고 컴파일된 그래프를 반환."""
    graph = StateGraph(ConsensusState)

    # 노드 등록 (stub)
    graph.add_node("persona_factory", _stub_node)
    graph.add_node("moderator_preselect", _stub_node)
    graph.add_node("multi_agent_dialogue", _stub_node)
    graph.add_node("consensus_assessment", _stub_node)
    graph.add_node("persona_voting", _stub_node)

    # 엣지: 순차 흐름
    graph.set_entry_point("persona_factory")
    graph.add_edge("persona_factory", "moderator_preselect")
    graph.add_edge("moderator_preselect", "multi_agent_dialogue")
    graph.add_edge("multi_agent_dialogue", "consensus_assessment")

    # 조건부 엣지: Node 4 → 루프백 or Node 5
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
