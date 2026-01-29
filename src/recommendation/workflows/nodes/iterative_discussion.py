from src.recommendation.workflows.states.recommendation_state import RecommendationState


def iterative_discussion_node(state: RecommendationState) -> dict:
    """합의/토론 노드"""
    # Mock Implementation
    current_rec = {
        "items": [
            {
                "restaurant_id": "6976b54010e1fa815903d4ce",
                "reasoning_description": "Best match",
            },
        ]
    }

    return {
        "current_recommendation": current_rec,
        "status_message": ["Iterative discussion completed"],
        "process_time": 10.0,
    }
