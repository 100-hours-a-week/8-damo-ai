# LangGraph 기본 설정
from langgraph.graph import StateGraph, START, END
from langgraph.store.memory import InMemoryStore
# State, Model 등 스키마 구조
from src.recommendation.workflows.states.recommendation_state import RecommendationState
from src.recommendation.schemas.recommendations_request import RecommendationsRequest
from src.recommendation.schemas.recommendations_response import RecommendationsResponse
# 노드
from src.recommendation.workflows.nodes.utility_node import (
    branch_node, error_branch_node, analyze_refresh_branch
)
from src.recommendation.workflows.nodes.restaurant_filtering import restaurant_filtering_node
from src.recommendation.workflows.nodes.analyze_refresh import analyze_refresh_node
# 내장 라이브러리
from datetime import datetime
# 서드파티 라이브러리

# from src.recommendation.workflows.nodes.analyze_refresh import analyze_refresh_node
# from src.recommendation.workflows.nodes.iterative_discussion import (
#     iterative_discussion_node,
# )
# from src.recommendation.workflows.nodes.persona_manager import persona_manager_node
# from src.recommendation.workflows.nodes.restaurant_filtering import (
#     restaurant_filtering_node,
# )
# from src.recommendation.workflows.nodes.recommendation import recommendation_node
# from src.recommendation.workflows.nodes.final_result import final_result_node
# from src.shared.nodes.graph_nodes import END
# from src.shared.nodes.memory_saver import MemorySaver
# from src.recommendation.workflows.edges.check_satisfication import check_satisfaction
# from src.recommendation.workflows.edges.check_max_iterations import check_max_iterations

def __initial_state(request: RecommendationsRequest) -> RecommendationState:
    is_vote_exists = request.vote_result_list is not None
    
    # 초기 상태 생성
    initial_state = RecommendationState(
        user_ids=request.user_ids,
        dining_id=request.dining_data.dining_id,
        dining_data=request.dining_data,
        rejected_restaurants=[],
        filtered_restaurants=[],
        current_recommendation={},
        personas=[],
        status_message=[
            "재추천 실행" if is_vote_exists else "최초 추천 실행",
            "프로세스 시작",
            f"현재 인원 : {len(request.user_ids)}명",
            f"인원 아이디 : {', '.join(map(str, request.user_ids))}",
        ],
        iteration_count=0,
        max_iterations=3,
        user_satisfied=False,
        process_start_time=datetime.now(),
        process_time=0.0,
        is_diffrent_user=False,
        is_empty_restaurants=False,
        is_error=False,
        error_message="",
    )

    # 분기 확인
    initial_state = {
        **initial_state,
        "is_initial_workflow": not is_vote_exists,
        "vote_result_list": request.vote_result_list
    }
    
    return initial_state


async def recommendation_workflow(request: RecommendationsRequest):
    """
    레스토랑 추천 워크플로우 그래프 생성

    Args:
        request: RecommendationsRequest

    Returns:
        RecommendationsResponse
    """
    # 1. 헬퍼 함수를 통한 초기 상태 생성
    initial_state = __initial_state(request)

    # 2. 그래프 생성
    workflow = StateGraph(RecommendationState)

    # 3. 노드 선언
    workflow.add_node("restaurant_filtering", restaurant_filtering_node)
    workflow.add_node("analyze_refresh", analyze_refresh_node)

    # 4. 엣지(연결) 구조
    workflow.add_conditional_edges(
        START,
        branch_node,
        {"restaurant_filtering": "restaurant_filtering", "analyze_refresh": "analyze_refresh"},
    )
    workflow.add_edge("restaurant_filtering", END)
    workflow.add_conditional_edges(
        "analyze_refresh",
        analyze_refresh_branch,
        {"filter": "restaurant_filtering", "error": END, "next": END},
    )

    _store = InMemoryStore()
    app = workflow.compile(store=_store)
    result_state = await app.ainvoke(initial_state)

    return result_state

