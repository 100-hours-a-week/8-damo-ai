from src.recommendation.workflows.states.recommendation_state import RecommendationState


def persona_manager_node(state: RecommendationState) -> dict:
    """페르소나 관리 노드"""
    # Mock Implementation
    personas = [
        {"user_id": 1, "persona": "Spicy lover"},
        {"user_id": 2, "persona": "Vegan"},
    ]
    return {
        "personas": personas,
        "status_message": ["Persona manager completed"],
        "process_time": 2.0,
    }
