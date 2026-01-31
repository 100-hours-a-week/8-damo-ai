from datetime import datetime
from typing import Any, Dict, List
from langgraph.store.memory import BaseStore
from src.recommendation.workflows.states.recommendation_state import RecommendationState
from src.shared.db.db_manager import MongoManager

async def load_db_node(state: RecommendationState, store: BaseStore) -> str:
    try:
        namespace = ("dining_sessions", str(state["dining_id"]))
        # 1. 기존 데이터 가져오기
        mongo_manager = MongoManager()
        mongo_manager.set_collection("dining_sessions")
        data = await mongo_manager.read_one({"diningId": state["dining_id"]})
        if data == None:
            raise Exception(f"Dining session not found for ID: {state['dining_id']}")
        
        store.put(namespace=namespace, key=str(state["dining_id"]), value=data)

        return state
    except Exception as e:
        print(e)
        return {
            **state,
            "is_error": True,
            "error_message": str(e),
        }