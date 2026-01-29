from datetime import datetime
from typing import Any, Dict, List

from src.recommendation.workflows.states.recommendation_state import RecommendationState

def branch_node(state: RecommendationState) -> str:
    """분기 노드"""
    if state["is_initial_workflow"] == True:
        return 'restaurant_filtering'
    else:
        return 'analyze_refresh'

def error_branch_node(state: RecommendationState) -> str:
    """DB 에러 분기 노드"""
    if state["is_error"] == True:
        return 'error'
    else:
        return 'next'