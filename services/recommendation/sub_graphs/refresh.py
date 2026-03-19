import logging

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from services.recommendation.state import RecommendationState
from shared.database.db_manager import DBManager

logger = logging.getLogger(__name__)

# 전역 사용
db_manager = DBManager()
db_manager.set_collection("dining_sessions")

async def is_user_group_valid(state: RecommendationState) -> RecommendationState:
    dining_id = state.get("dining_id")
    dining_session = await db_manager.read_one({"diningId": int(dining_id)})
    if dining_session is None:
        logger.warning("[REFRESH] dining_session 없음 → END: dining_id=%s", dining_id)
        return Command(update={
            "error_message": f"Dining session not found: {dining_id}",
            "status_message": f"회식 세션(ID: {dining_id}) 정보를 찾을 수 없어 추천을 중단합니다."
        }, goto=END)
    
    current_user_ids = state.get("user_ids")
    prev_user_ids = dining_session.get("userIds")

    if set(current_user_ids) == set(prev_user_ids):
        logger.info("[REFRESH] 동일 유저 그룹, DB 후보 확인: dining_id=%s", dining_id)
        return Command(update={
            "iteration_count": dining_session.get("currentPhase", 0),
            "error_message": f"User ids are same: {dining_id}",
            "status_message": f"회식 세션(ID: {dining_id})에 참여한 유저가 변경되지 않았습니다."
        }, goto="is_remaining_candidate")
    else:
        logger.info("[REFRESH] 유저 그룹 변경, AI 신규 추천으로: dining_id=%s", dining_id)
        return Command(update={
            "error_message": f"User ids are different: {dining_id}",
            "status_message": f"회식 세션(ID: {dining_id})에 참여한 유저가 변경되었습니다."
        }, goto="recommend", graph=Command.PARENT)

async def is_remaining_candidate(state: RecommendationState) -> RecommendationState:
    dining_id = int(state.get("dining_id"))
    dining_session = await db_manager.read_one({"diningId": dining_id})
    
    try:
        # 1. DB에서 후보군 가져오기
        candidate = dining_session.get("restaurantCandidate", [])
        
        # [Pre-check] 아예 없으면 즉시 신규 추천(AI)으로 이동
        if not candidate:
            raise Exception("No more candidates in DB")
        # 2. 방금 사용자가 거절한(리프레시 누른) 식당들 식별
        # state의 vote_result_list에 정보가 있다면 이를 가공하고, 없으면 candidate 상단을 사용
        vote_results = state.get("vote_result_list", [])
        if vote_results:
            # DB와 포맷을 맞추기 위해 _id를 포함한 객체 리스트로 생성
            prev_candidate = [{"_id": v.restaurant_id} for v in vote_results]
        else:
            prev_candidate = candidate[:5]
        # 3. [Case: 후보가 5개 이하일 때] -> 남은 거 다 보여주고 DB 비우기
        if 0 < len(candidate) <= 5:
            new_candidate = list(candidate) # 전체 복사
            
            await db_manager.update_one_with_command(
                {"diningId": dining_id},
                {
                    "$push": {"rejectedCandidate": {"$each": prev_candidate}},
                    "$set": {"restaurantCandidate": []}
                }
            )
        # 4. [Case: 후보가 5개 이상일 때] -> 기존처럼 5개씩 슬라이싱
        else:
            new_candidate = candidate[:5]
            
            await db_manager.update_one_with_command(
                {"diningId": dining_id},
                {
                    "$push": {"rejectedCandidate": {"$each": prev_candidate}},
                    "$pullAll": {"restaurantCandidate": new_candidate}
                }
            )

        # 5. 결과 반환 → bridge → agent_dialogue로 자연스럽게 진행
        return {
            "status_message": f"기존 후보군 {len(new_candidate)}개로 AI 토론 시작합니다.",
            "filtered_restaurant": new_candidate,
        }

    except Exception as e:
        # 후보가 하나도 없거나 에러 발생 시 부모의 recommend(AI 연산) 노드로 이동
        logger.info("[REFRESH] DB 후보 소진, AI 신규 추천으로 전환: dining_id=%s, reason=%s", dining_id, e)
        return Command(update={
            "error_message": f"No candidate restaurants found: {dining_id}",
            "status_message": "보여드릴 남은 후보가 없어 AI 신규 추천을 시작합니다."
        }, goto="recommend", graph=Command.PARENT)

# 메인 그래프
def get_refresh_graph():
    workflow = StateGraph(RecommendationState)
    workflow.add_node("is_user_group_valid", is_user_group_valid)
    workflow.add_node("is_remaining_candidate", is_remaining_candidate)

    workflow.add_edge(START, "is_user_group_valid")
    
    return workflow.compile().with_config({"run_name": "refresh_sub_graph"})