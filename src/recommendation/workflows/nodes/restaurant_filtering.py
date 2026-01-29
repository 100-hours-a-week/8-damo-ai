from src.recommendation.workflows.states.recommendation_state import RecommendationState


def restaurant_filtering_node(state: RecommendationState) -> dict:
    """레스토랑 필터링 노드"""
    # Mock Implementation
    filtered = [
        {"id": "6976b54010e1fa815903d4ce", "name": "Mock Restaurant 1"},
        {"id": "6976b57f10e1fa815903d4cf", "name": "Mock Restaurant 2"},
    ]
    return {
        "filtered_restaurants": filtered,
        "status_message": ["Restaurant filtering completed"],
        "process_time": 2.0,
    }
