from src.recommendation.workflows.states.recommendation_state import RecommendationState


def check_satisfaction(state: RecommendationState) -> str:
    """사용자 만족도 체크"""
    if state.get("user_satisfied", False):
        return "satisfied"
    return "not_satisfied"
