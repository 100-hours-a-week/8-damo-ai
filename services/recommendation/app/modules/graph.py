import os, re, yaml
from datetime import datetime
from typing import TypedDict, Optional, Dict
from services.recommendation.app.modules.state import RecommendationState
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from services.recommendation.app.modules.sub_graphs.refresh import get_refresh_graph
from services.recommendation.app.modules.sub_graphs.recommend import get_recommend_graph

from shared.monitoring import get_langfuse_handler, get_langfuse_client

# get_langfuse_client()

# 분기 노드
def recommend_refresh_branch_node(state: RecommendationState) -> str:
    """분기 노드"""
    vote_result_list = state.get("vote_result_list") 
    if len(vote_result_list) == 0:
        return 'recommend'
    else:
        return 'refresh'

# 메인 그래프
def get_recommendation_graph():
    workflow = StateGraph(RecommendationState)

    workflow.add_conditional_edges(
        START,
        recommend_refresh_branch_node,
        {
            "recommend": "recommend",
            "refresh": "refresh",
        },
    )

    workflow.add_node("refresh", get_refresh_graph())
    workflow.add_node("recommend", get_recommend_graph())

    workflow.add_edge("recommend", END)
    workflow.add_edge("refresh", END)

    handler = get_langfuse_handler()
    return workflow.compile().with_config({"callbacks": [handler]})