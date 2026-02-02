from datetime import datetime
from typing import Any, Dict, List

from src.recommendation.workflows.states.recommendation_state import RecommendationState

def branch_node(state: RecommendationState) -> str:
    """분기 노드"""
    if state.get("user_ids") == [10101010]:
        return "mock_node"
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

def analyze_refresh_branch(state: RecommendationState) -> str:
    if state.get("is_error"):
        return "error"
    # 서브그래프에서 심어놓은 플래그 확인
    if state.get("is_diffrent_user") or state.get("is_empty_restaurants"):
        return "filter"
    return "next"
