from langgraph.graph import StateGraph, START, END
from datetime import datetime
from src.recommendation.workflows.states.recommendation_state import RecommendationState
# 서브 노드
from src.recommendation.features.restaurant_filtering.nodes.distance_node import distance_node
from src.recommendation.features.restaurant_filtering.nodes.allergy_node import allergy_node
from src.recommendation.features.restaurant_filtering.nodes.budget_node import budget_node

# 에러 처리 노드
def __error_handler_node(state: RecommendationState) -> str:
    if state.get("is_error"):
        return "error"
    return "next"

sub_builder = StateGraph(RecommendationState)

# 프로덕션 용
# 1. 서브 그래프 조립
sub_builder.add_node("distance", distance_node)
sub_builder.add_node("allergy", allergy_node)
sub_builder.add_node("budget", budget_node)
# 2. 서브 그래프 연결
sub_builder.add_edge(START, "distance")
sub_builder.add_conditional_edges("distance", __error_handler_node, {"error": END, "next": "allergy"})
sub_builder.add_conditional_edges("allergy", __error_handler_node, {"error": END, "next": "budget"})
sub_builder.add_edge("budget", END)

# # 디버그 용
# # 1. 서브 그래프 조립
# sub_builder.add_node("distance", distance_node)
# sub_builder.add_node("budget", budget_node)
# # 2. 서브 그래프 연결
# sub_builder.add_edge(START, "distance")
# sub_builder.add_conditional_edges("distance", __error_handler_node, {"error": END, "next": "budget"})
# sub_builder.add_edge("budget", END)


# 3. 컴파일
restaurant_filtering_node = sub_builder.compile()