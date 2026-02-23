from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from services.recommendation.app.modules.state import RecommendationState

# 거리 그래프
from shared.database.db_manager import DBManager

# 거리 노드
async def distance_node(state: RecommendationState) -> RecommendationState:
    db_manager = DBManager()
    db_manager.set_collection("restaurants")
    _X = float(state.get("dining_data", {}).get("x"))
    _Y = float(state.get("dining_data", {}).get("y"))
    MAX_DISTANCE = 1000 # 1km

    # 1. 거리 가까운 식당 가져오기
    restaurants = await db_manager.find_by_location(_X, _Y, MAX_DISTANCE)
    
    if not restaurants or len(restaurants) == 0:
        return Command(update={
            "filtered_restaurants": [],
            "status_message": "필터링된 식당이 없습니다",
            "error_message": f"No Restaurant from the location ({_X}, {_Y})"
        }, goto=END)

    # 2. 거리 점수 계산 (1.0 ~ 0.0)
    import math
    def calculate_haversine(lon1, lat1, lon2, lat2):
        R = 6371000 # 지구 반지름 (m)
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    for res in restaurants:
        coords = res.get("location", {}).get("coordinates", [0, 0])
        dist = calculate_haversine(_X, _Y, coords[0], coords[1])
        
        # 가까울수록 1.0, 1km 지점이면 0.0
        score = max(0.0, 1.0 - (dist / MAX_DISTANCE))
        res["distance_score"] = round(score, 4)
        res["distance"] = int(dist) # 실제 거리(m)도 저장

    # 3. 점수 기반 정렬 (내림차순: 점수 높은/가까운 식당 우선)
    restaurants.sort(key=lambda x: x["distance_score"], reverse=True)

    return Command(update={
        "filtered_restaurants": restaurants,
        "status_message": f"거리 필터링 완료: {len(restaurants)}개 검색됨 (가까운 순 정렬)"
    }, goto="allergy")

def _scoring_allergy(user_datas: list[dict], filtered_restaurants: list[dict]) -> list[dict]:
    def _calculate_dynamic_score(menus: list[dict], allergy: str) -> float:
        """메뉴 기반 실시간 알러지 위험도 계산 (가중치 적용)"""
        if not menus:
            return 0.0
        
        keywords = ALLERGY_KEYWORDS.get(allergy, [allergy.lower()])
        total_weight = 0.0
        matched_weight = 0.0
        
        for idx, menu in enumerate(menus):
            name = menu.get("name", "").lower()
            # [강화] 대표 메뉴(상위 3개)는 가중치 2배 적용
            weight = 2.0 if idx < 3 else 1.0
            total_weight += weight
            
            if any(kw in name for kw in keywords):
                matched_weight += weight
                
        return round(matched_weight / total_weight, 4)
    
    final_list = []
    veto_limit = len(user_datas) // 3
    for res in filtered_restaurants:
        risky_users = 0
        res_reasoning_data = [] # LLM을 위한 힌트 저장
        
        # 식당의 KAG 데이터 가져오기 (미리 계산된 맵)
        kag_risk_map = res.get("allergy_risk_map", {}) 
        for user in user_datas:
            user_allergies = user.get("allergies", [])
            max_risk_for_this_user = 0.0
            
            for allergy in user_allergies:
                # 1. KAG 점수 확인
                kag_score = kag_risk_map.get(allergy, 0.0)
                
                # 2. 동적 점수 계산 (메뉴 매칭 - KAG 보완용)
                dynamic_score = _calculate_dynamic_score(res.get("menus", []), allergy)
                
                # 3. 혼합 점수 (KAG를 우선하되 데이터 없으면 동적 점수 사용)
                combined_score = max(kag_score, dynamic_score)
                max_risk_for_this_user = max(max_risk_for_this_user, combined_score)
                
                if combined_score >= 0.5:
                    res_reasoning_data.append(f"유저 {user['id']}님의 {allergy} 알러지 위험군")
            if max_risk_for_this_user >= 0.5:
                risky_users += 1
        # 4. 필터링 및 힌트 기록
        if risky_users < veto_limit:
            res["allergy_reasoning_hints"] = res_reasoning_data # 다음 노드(LLM)가 쓸 재료
            res["risky_user_count"] = risky_users
            final_list.append(res)

    return final_list

# 알러지 노드
async def allergy_node(state: RecommendationState) -> RecommendationState:
    db_manager = DBManager()
    db_manager.set_collection("users")
    user_datas = []
    for user_id in state.get("user_ids"):
        user_data = await db_manager.read_one({
            "id": { "$in": [str(user_id), int(user_id)] }
        })
        if user_data is None:
            return Command(
                update={
                    "filtered_restaurants": [],
                    "error_message": f"User not found in DB: {user_id}",
                    "status_message": f"유저(ID: {user_id}) 정보를 찾을 수 없어 추천을 중단합니다."
                },
                goto=END
            )
        user_datas.append(user_data)
    
    # 알러지 필터링
    filtered_restaurants = _scoring_allergy(user_datas, state.get("filtered_restaurants"))
    print(filtered_restaurants)

    return Command(update={
        "status_message": "알러지 필터링 완료"
    }, goto=END)

# 메인 그래프
def get_recommend_graph():
    workflow = StateGraph(RecommendationState)

    workflow.add_edge(START, "distance")
    workflow.add_node("distance", distance_node)
    workflow.add_node("allergy", allergy_node)


    return workflow.compile().with_config({"run_name": "recommend_sub_graph"})
