from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from services.recommendation.app.modules.state import RecommendationState
from shared.database.db_manager import DBManager

# 전역 사용
db_manager = DBManager()
db_manager.set_collection("dining_sessions")

async def is_user_group_valid(state: RecommendationState) -> RecommendationState:
    dining_session = await db_manager.read_one({"_id": state.get("dining_id")})
    if dining_session is None:
        return Command(update={
            "error_message": f"Dining session not found: {state.get('dining_id')}",
            "status_message": f"회식 세션(ID: {state.get('dining_id')}) 정보를 찾을 수 없어 추천을 중단합니다."
        }, goto=END)
    
    current_user_ids = state.get("user_ids")
    prev_user_ids = dining_session.get("userIds")

    if set(current_user_ids) == set(prev_user_ids):
        return Command(update={
            "error_message": f"User ids are same: {state.get('dining_id')}",
            "status_message": f"회식 세션(ID: {state.get('dining_id')})에 참여한 유저가 변경되지 않았습니다."
        }, goto="is_remaining_candidate")
    else:
        return Command(update={
            "error_message": f"User ids are different: {state.get('dining_id')}",
            "status_message": f"회식 세션(ID: {state.get('dining_id')})에 참여한 유저가 변경되었습니다."
        }, goto="recommend", graph=Command.PARENT)

async def is_remaining_candidate(state: RecommendationState) -> RecommendationState:
    dining_session = await db_manager.read_one({"_id": state.get("dining_id")})
    try:
        candidate = dining_session.get("restaurantCandidate")
        prev_candidate = candidate[:5]
        new_candidate = candidate[5:10]

        await db_manager.update_one_with_command({"_id": state.get("dining_id")}, {"$push": {"rejectedCandidates": {"$each": prev_candidate}}})
        await db_manager.update_one_with_command({"_id": state.get("dining_id")}, {"$pull": {"restaurantCandidate": {"$each": new_candidate}}})

        return Command(update={
            "status_message": f"회식 세션(ID: {state.get('dining_id')})에 새로운 식당을 추천합니다.",
            "recommeded_items": new_candidate
        }, goto=END)

    except Exception as e:
        return Command(update={
            "error_message": f"No candidate restaurants found: {state.get('dining_id')}",
            "status_message": f"회식 세션(ID: {state.get('dining_id')})에 남은 후보 식당이 없습니다."
        }, goto="recommend", graph=Command.PARENT)

# 메인 그래프
def get_refresh_graph():
    workflow = StateGraph(RecommendationState)
    workflow.add_node("is_user_group_valid", is_user_group_valid)
    workflow.add_node("is_remaining_candidate", is_remaining_candidate)

    workflow.add_edge(START, "is_user_group_valid")
    
    return workflow.compile().with_config({"run_name": "refresh_sub_graph"})