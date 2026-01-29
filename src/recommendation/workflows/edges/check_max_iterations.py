from src.recommendation.workflows.states.recommendation_state import RecommendationState


def check_max_iterations(state: RecommendationState) -> str:
    """최대 반복 횟수 체크"""
    max_iter = state.get("max_iterations", 5)
    if state["iteration_count"] >= max_iter:
        return "max_reached"
    return "continue"
