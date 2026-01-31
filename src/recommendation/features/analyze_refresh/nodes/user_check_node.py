from langgraph.store.memory import BaseStore
from src.recommendation.workflows.states.recommendation_state import RecommendationState

async def user_check_node(state: RecommendationState, store: BaseStore) -> RecommendationState:
    try:
        namespace = ("dining_sessions", str(state["dining_id"]))
        # 1. 기존 데이터 가져오기
        data = store.get(namespace=namespace, key=str(state["dining_id"]))
        if data == None:
            raise Exception("Previous dining session not found")
        
        # 2. 사용자 ID 확인
        session_data = data.value
        user_ids = session_data.get("userIds") or session_data.get("user_ids", [])
        if not user_ids:
            raise Exception("User IDs not found in dining session")
        
        # 3. 사용자 ID가 일치하는지 확인
        if state["user_ids"] != user_ids:
           return {
                "is_diffrent_user": True,
                "is_empty_restaurants": False,
                "is_error": False,
                "error_message": "",
           }
        else:
            return {
                "is_diffrent_user": False,
                "is_empty_restaurants": False,
                "is_error": False,
                "error_message": "",
            } 
    except Exception as e:
        print(e)
        return {
            "is_diffrent_user": False,
            "is_empty_restaurants": False,
            "is_error": True,
            "error_message": str(e),
        }

def user_check_branch_node(state: RecommendationState, store: BaseStore) -> str:
    # 플래그가 True가 되었으면 서브그래프를 즉시 종료(END)하여 부모에게 알림
    if state.get("is_diffrent_user"):
        return "goto_filter"
    return "next"