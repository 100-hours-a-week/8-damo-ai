from langgraph.graph import END, StateGraph

from services.iterative_discussion.app.engine.state import ConsensusState
from services.iterative_discussion.app.nodes.consensus_assessment import consensus_assessment
from services.iterative_discussion.app.nodes.moderator_preselect import moderator_preselect
from services.iterative_discussion.app.nodes.multi_agent_dialogue import multi_agent_dialogue
from services.iterative_discussion.app.nodes.persona_factory import persona_factory
from services.iterative_discussion.app.nodes.persona_voting import persona_voting


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

    # 노드 등록
    graph.add_node("persona_factory", persona_factory)
    graph.add_node("moderator_preselect", moderator_preselect)
    graph.add_node("multi_agent_dialogue", multi_agent_dialogue)
    graph.add_node("consensus_assessment", consensus_assessment)
    graph.add_node("persona_voting", persona_voting)

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
