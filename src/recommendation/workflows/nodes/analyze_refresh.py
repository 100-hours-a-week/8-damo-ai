from src.recommendation.workflows.states.recommendation_state import RecommendationState
from src.shared.db.db_manager import MongoManager

async def analyze_refresh_node(state: RecommendationState) -> RecommendationState:
    """분석 및 새로고침 노드"""

    try:
        # 1. 기존 데이터 가져오기
        mongo_manager = MongoManager()
        mongo_manager.set_collection("dining_sessions")
        data = await mongo_manager.read_one({"diningId": state["dining_id"]})
        if data == None:
            raise Exception("Dining session not found")
        # 2. 데이터 분석(현재는 X)
        # 3. state 업데이트

        return state
    except Exception as e:
        print(e)
        return {
            **state,
            "is_error": True,
            "error_message": str(e),
        }
    

    
