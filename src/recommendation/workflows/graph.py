from datetime import datetime
from langgraph.graph import StateGraph, START, END
from src.recommendation.schemas.requests.recommendation_request import (
    RecommendationState,
    RecommendationRequest,
)
from src.shared.nodes.graph_nodes import (
    record_start_time_node,
    record_end_time_node,
    random_delay_node,
)


async def recommendations_v1(
    request: RecommendationRequest, is_refresh: bool = False, refresh_count: int = 0
):
    builder = StateGraph(RecommendationState)

    # 공통 노드 추가
    builder.add_node("start_timer", record_start_time_node)
    builder.add_node("random_delay", random_delay_node)
    builder.add_node("end_timer", record_end_time_node)

    # 흐름 연결
    builder.add_edge(START, "start_timer")
    builder.add_edge("start_timer", "random_delay")
    builder.add_edge("random_delay", "end_timer")
    builder.add_edge("end_timer", END)

    graph = builder.compile()

    initial_state = {
        "user_data": [],
        "dining_data": request.dining_data,
        "is_refresh": is_refresh,
        "refresh_count": refresh_count,
        "is_success": False,
        "status_message": [],
        "process_start_time": datetime.now(),
        "process_time": 0.0,
    }

    final_state = await graph.ainvoke(initial_state)

    return final_state
