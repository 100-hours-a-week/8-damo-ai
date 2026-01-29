from langgraph.graph import StateGraph
from src.recommendation.workflows.states.recommendation_state import RecommendationState
from src.recommendation.workflows.nodes.analyze_refresh import analyze_refresh_node
from src.recommendation.workflows.nodes.iterative_discussion import (
    iterative_discussion_node,
)
from src.recommendation.workflows.nodes.persona_manager import persona_manager_node
from src.recommendation.workflows.nodes.restaurant_filtering import (
    restaurant_filtering_node,
)
from src.recommendation.workflows.nodes.recommendation import recommendation_node
from src.recommendation.workflows.nodes.final_result import final_result_node
from src.shared.nodes.graph_nodes import END
from src.shared.nodes.memory_saver import MemorySaver
from src.recommendation.workflows.edges.check_satisfication import check_satisfaction
from src.recommendation.workflows.edges.check_max_iterations import check_max_iterations


def create_restaurant_recommendation_graph():
    """레스토랑 추천 워크플로우 그래프 생성"""

    workflow = StateGraph(RecommendationState)

    # 노드 추가
    workflow.add_node("restaurant_filtering", restaurant_filtering_node)
    workflow.add_node("persona_manager", persona_manager_node)
    workflow.add_node("iterative_discussion", iterative_discussion_node)
    workflow.add_node("recommend", recommendation_node)
    workflow.add_node("analyze_refresh", analyze_refresh_node)
    workflow.add_node("final_result", final_result_node)

    # 시작점
    workflow.set_entry_point("restaurant_filtering")

    # 순차 엣지
    workflow.add_edge("restaurant_filtering", "iterative_discussion")
    workflow.add_edge("persona_manager", "iterative_discussion")
    workflow.add_edge("iterative_discussion", "recommend")

    # 조건부 엣지: 만족도 체크
    workflow.add_conditional_edges(
        "recommend",
        check_satisfaction,
        {"satisfied": END, "not_satisfied": "check_iterations"},
    )

    # 반복 횟수 체크용 더미 노드
    workflow.add_node("check_iterations", lambda x: x)
    workflow.add_conditional_edges(
        "check_iterations",
        check_max_iterations,
        {"max_reached": "final_result", "continue": "analyze_refresh"},
    )

    # 순환 엣지
    workflow.add_edge("analyze_refresh", "restaurant_filtering")
    workflow.add_edge("analyze_refresh", "iterative_discussion")
    workflow.add_edge("analyze_refresh", "persona_manager")
    workflow.add_edge("final_result", END)

    # 메모리 체크포인터
    memory = MemorySaver()

    return workflow.compile(checkpointer=memory)
