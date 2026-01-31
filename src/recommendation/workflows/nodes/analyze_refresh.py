from langgraph.graph import StateGraph, START, END
from src.recommendation.workflows.states.recommendation_state import RecommendationState
from src.shared.db.db_manager import MongoManager
# 노드
from src.recommendation.features.analyze_refresh.nodes.load_db_node import load_db_node
from src.recommendation.features.analyze_refresh.nodes.user_check_node import user_check_node, user_check_branch_node
from src.recommendation.features.analyze_refresh.nodes.restaurant_list_node import restaurant_list_node

# 에러 처리 노드
def __error_handler_node(state: RecommendationState) -> str:
    if state.get("is_error"):
        return "error"
    return "next"

# 1. 서브 그래프 조립
sub_builder = StateGraph(RecommendationState)
sub_builder.add_node("load_db", load_db_node)
sub_builder.add_node("user_check", user_check_node)
sub_builder.add_node("restaurant_list", restaurant_list_node)

# 2. 서브 그래프 연결
sub_builder.add_edge(START, "load_db")
sub_builder.add_conditional_edges("load_db", __error_handler_node, {"error": END, "next": "user_check"})
sub_builder.add_conditional_edges("user_check", user_check_branch_node, {"goto_filter": END, "next": "restaurant_list"})
sub_builder.add_edge("restaurant_list", END)

# 3. 컴파일
analyze_refresh_node = sub_builder.compile()


