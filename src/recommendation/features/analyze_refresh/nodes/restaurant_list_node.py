from datetime import datetime
from typing import Any, Dict, List
from langgraph.store.memory import BaseStore
from src.recommendation.workflows.states.recommendation_state import RecommendationState
from src.shared.db.db_manager import MongoManager

async def restaurant_list_node(state: RecommendationState, store: BaseStore) -> RecommendationState:
    try:
        namespace = ("dining_sessions", str(state["dining_id"]))
        prev_dining_session = store.get(namespace=namespace, key=str(state["dining_id"]))
        prev_candidates = prev_dining_session.value["restaurantCandidate"]

        if len(prev_candidates) > 5:
            new_restaurant_candidate = prev_candidates[5:]
            return {
                **state,
                "rejected_restaurants": prev_candidates[:5],
                "filtered_restaurants": new_restaurant_candidate,
            }
        else:
            return {
                **state,
                "rejected_restaurants": prev_candidates,
                "is_empty_restaurants": True
            }
    except Exception as e:
        print(e)
        return {
            **state,
            "is_error": True,
            "error_message": str(e),
        }
