from langgraph.graph import END, StateGraph

from services.iterative_discussion.app.engine.state import ConsensusState
from services.iterative_discussion.app.nodes.consensus_assessment import (
    consensus_assessment,
)
from services.iterative_discussion.app.nodes.moderator_preselect import (
    moderator_preselect,
)
from services.iterative_discussion.app.nodes.multi_agent_dialogue import (
    multi_agent_dialogue,
)
from services.iterative_discussion.app.nodes.restaurant_summarizer import (
    restaurant_summarizer,
)
from services.iterative_discussion.app.nodes.persona_factory import persona_factory
from services.iterative_discussion.app.nodes.persona_voting import persona_voting
from services.iterative_discussion.app.nodes.reason_generator import reason_generator
from services.iterative_discussion.app.nodes.self_evolution import self_evolution


def _check_error(state: ConsensusState) -> str:
    """에러 발생 시 즉시 END로 단축."""
    if state.get("is_error"):
        return "end"
    return "continue"


def _after_dialogue(state: ConsensusState) -> str:
    """Node 3 이후: min_rounds 미달 시 합의 판정 스킵."""
    if state.get("is_error"):
        return "end"
    current_round = state.get("round", 0)
    min_rounds = state.get("min_rounds", 2)
    if current_round < min_rounds:
        return "dialogue"  # 합의 판정 건너뛰고 바로 다음 라운드
    return "assess"  # 합의 판정으로


def _should_continue(state: ConsensusState) -> str:
    """Node 4 이후 조건부 엣지: 루프백 or 투표 진행."""
    if state.get("is_error"):
        return "end"
    if state.get("consensus_reached") or state.get("round", 0) >= state.get(
        "max_rounds", 3
    ):
        return "vote"
    # 거부된 식당이 있으면 → preselect로 돌아가서 후보 교체
    if state.get("rejected_restaurant_ids"):
        return "preselect"
    return "dialogue"


def build_consensus_graph() -> StateGraph:
    """5노드 flat graph를 빌드하고 컴파일된 그래프를 반환."""
    graph = StateGraph(ConsensusState)

    # 노드 등록
    graph.add_node("persona_factory", persona_factory)
    graph.add_node("self_evolution", self_evolution)
    graph.add_node("moderator_preselect", moderator_preselect)
    graph.add_node("restaurant_summarizer", restaurant_summarizer)
    graph.add_node("multi_agent_dialogue", multi_agent_dialogue)
    graph.add_node("consensus_assessment", consensus_assessment)
    graph.add_node("persona_voting", persona_voting)
    graph.add_node("reason_generator", reason_generator)

    # 엔트리
    graph.set_entry_point("persona_factory")

    # persona_factory → 에러 체크 → self_evolution
    graph.add_conditional_edges(
        "persona_factory",
        _check_error,
        {"continue": "self_evolution", "end": END},
    )

    # self_evolution → moderator_preselect (항상 통과, 에러 없음)
    graph.add_edge("self_evolution", "moderator_preselect")

    # moderator_preselect → 에러 체크 → restaurant_summarizer
    graph.add_conditional_edges(
        "moderator_preselect",
        _check_error,
        {"continue": "restaurant_summarizer", "end": END},
    )

    # restaurant_summarizer → multi_agent_dialogue (항상 통과, 에러 없음)
    graph.add_edge("restaurant_summarizer", "multi_agent_dialogue")

    # multi_agent_dialogue → min_rounds 체크 → 스킵 or 합의 판정
    graph.add_conditional_edges(
        "multi_agent_dialogue",
        _after_dialogue,
        {
            "dialogue": "multi_agent_dialogue",  # min_rounds 미달 → 스킵
            "assess": "consensus_assessment",  # min_rounds 충족 → 판정
            "end": END,
        },
    )

    # Node 4 → 조건부: 루프백 or Node 5
    graph.add_conditional_edges(
        "consensus_assessment",
        _should_continue,
        {
            "dialogue": "multi_agent_dialogue",
            "preselect": "moderator_preselect",
            "vote": "persona_voting",
            "end": END,
        },
    )

    graph.add_edge("persona_voting", "reason_generator")
    graph.add_edge("reason_generator", END)

    return graph.compile()
