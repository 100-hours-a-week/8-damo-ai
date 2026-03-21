import logging

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from services.recommendation.state import RecommendationState
from time import time

logger = logging.getLogger(__name__)

# 알러지 키워드 매핑
ALLERGY_KEYWORDS = {
    "LEGUMES": ["콩", "대두", "완두", "강낭콩"],
    "NUTS": ["땅콩", "호두", "잣", "캐슈넛", "아몬드"],
    "SHELLFISH": ["조개", "굴", "전복", "소라", "해방풍"],
    "FISH": ["생선", "고등어", "연어", "조기", "갈치"],
    "GRAINS": ["밀", "보리", "곡물", "호밀"],
    "MILK": ["우유", "치즈", "버터", "크림", "유제품"],
    "SHRIMP": ["새우", "대하", "중하"],
    "OYSTER": ["굴", "석화"],
    "CRAB": ["게", "대게", "킹크랩"],
    "MUSSEL": ["홍합"],
    "SQUID": ["오징어", "낙지", "문어"],
    "ABALONE": ["전복"],
    "MACKEREL": ["고등어"],
    "BUCKWHEAT": ["메밀", "소바"],
    "WHEAT": ["밀가루", "소맥"],
    "SOYBEAN": ["대두", "콩"],
    "WALNUT": ["호두"],
    "PEANUT": ["땅콩"],
    "PINE_NUT": ["잣"],
    "EGG": ["계란", "달걀", "난류"],
    "BEEF": ["소고기", "쇠고기", "육회"],
    "PORK": ["돼지고기", "제육", "삼겹살"],
    "CHICKEN": ["닭고기", "치킨"],
    "PEACH": ["복숭아"],
    "TOMATO": ["토마토"],
    "SULFITES": ["아황산", "방부제"]
}

# 거리 그래프
from shared.database.db_manager import DBManager

# 거리 노드
async def distance_node(state: RecommendationState) -> RecommendationState:
    db_manager = DBManager()
    db_manager.set_collection("restaurants")
    dining_id = state.get("dining_data", {}).get("dining_id") or state.get("dining_id")
    _X = float(state.get("dining_data", {}).get("x"))
    _Y = float(state.get("dining_data", {}).get("y"))
    MAX_DISTANCE = 1000 # 1km

    logger.info("[DISTANCE] 시작: dining_id=%s, x=%s, y=%s", dining_id, _X, _Y)

    # 1. 거리 가까운 식당 가져오기
    restaurants = await db_manager.find_by_location(_X, _Y, MAX_DISTANCE)
    logger.info("[DISTANCE] 조회 결과: %d개", len(restaurants) if restaurants else 0)

    # 2. 리프레시 시 이전에 추천한 식당 제외
    if not state.get("is_initial_workflow", True):
        excluded_ids: set[str] = set()

        # DB의 rejectedCandidate (이전 phase에서 보여준 식당 전체)
        try:
            session_db = DBManager()
            session_db.set_collection("dining_sessions")
            session = await session_db.read_one({"diningId": int(dining_id)})
            if session:
                for r in session.get("rejectedCandidate", []):
                    excluded_ids.add(str(r.get("_id", "")))
                for r in session.get("restaurantCandidate", []):
                    excluded_ids.add(str(r.get("_id", "")))
        except Exception as e:
            logger.warning("[DISTANCE] 이전 추천 식당 조회 실패 (무시): %s", e)

        # vote_result_list (현재 배치: 방금 거절된 식당)
        for v in state.get("vote_result_list", []):
            rid = v.get("restaurant_id") if isinstance(v, dict) else getattr(v, "restaurant_id", "")
            if rid:
                excluded_ids.add(str(rid))

        before = len(restaurants)
        restaurants = [r for r in restaurants if str(r.get("_id", "")) not in excluded_ids]
        logger.info(
            "[DISTANCE] 리프레시 중복 제거: %d개 제외 → %d개 남음",
            before - len(restaurants),
            len(restaurants),
        )

    if not restaurants or len(restaurants) == 0:
        logger.warning("[DISTANCE] 반경 내 식당 없음 → END: dining_id=%s", dining_id)
        return {
            "is_error": True,
            "filtered_restaurant": [],
            "status_message": "필터링된 식당이 없습니다",
            "error_message": f"No Restaurant from the location ({_X}, {_Y})",
        }

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

    return {
        "filtered_restaurant": restaurants,
        "status_message": f"거리 필터링 완료: {len(restaurants)}개 검색됨 (가까운 순 정렬)",
    }

def _scoring_allergy(user_datas: list[dict], filtered_restaurant: list[dict]) -> list[dict]:
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
    for res in filtered_restaurant:
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
    logger.info("[ALLERGY] 시작: user_ids=%s", state.get("user_ids"))
    db_manager = DBManager()
    db_manager.set_collection("users")
    user_datas = []
    for user_id in state.get("user_ids"):
        user_data = await db_manager.read_one({
            "id": { "$in": [str(user_id), int(user_id)] }
        })
        if user_data is None:
            logger.warning("[ALLERGY] 유저 없음 → END: user_id=%s", user_id)
            return Command(
                update={
                    "filtered_restaurant": [],
                    "error_message": f"User not found in DB: {user_id}",
                    "status_message": f"유저(ID: {user_id}) 정보를 찾을 수 없어 추천을 중단합니다."
                },
                goto=END
            )
        user_datas.append(user_data)

    # 알러지 필터링
    filtered_restaurant = _scoring_allergy(user_datas, state.get("filtered_restaurant"))
    logger.debug("[ALLERGY] 필터링 결과: %d개", len(filtered_restaurant))
    logger.info("[ALLERGY] 완료: %d개 식당 생존", len(filtered_restaurant))

    return Command(update={
        "status_message": "알러지 필터링 완료"
    }, goto=END)

# 예산 노드
async def budget_node(state: RecommendationState) -> dict:
    logger.info("[BUDGET] 시작: filtered_restaurant=%d개", len(state.get("filtered_restaurant", [])))
    start_time = time()
    total_budget = state["dining_data"].get("budget", 0)
    member_count = len(state["user_ids"])
    
    if total_budget <= 0 or member_count <= 0:
        return {"status_message": "예산 정보 부족으로 필터링을 스킵합니다."}

    _final_filtered = []
    # 주류 및 음료 키워드
    DRINK_KEYWORDS = ["소주", "맥주", "음료", "콜라", "사이다", "주류", "와인", "에이드", "커피", "티", "주스", "환타", "동동주", "막걸리", "하이볼"]

    for restaurant in state["filtered_restaurant"]:
        menus = restaurant.get("menus", [])
        
        # 1. 메뉴 분류 (가격 정보가 있는 것만)
        meals, drinks, sides = [], [], []
        for m in menus:
            title = m.get("title", "")
            price = m.get("price") or 0
            if not title or price <= 0: continue
            
            if any(k in title for k in DRINK_KEYWORDS):
                drinks.append(m)
            elif price >= 8000: # 8,000원 이상은 메인 식사로 간주
                meals.append(m)
            else:
                sides.append(m)

        # 2. 메인 메뉴 검토
        if not meals:
            _final_filtered.append(restaurant)
            continue
            
        # 가장 비중 있는 첫 번째 메인 메뉴 기준
        representative_meal = meals[0]
        full_meal_cost = representative_meal['price'] * member_count
        
        # [체크 1] 전원 메인 주문이 가능한가?
        if full_meal_cost > total_budget:
            continue # 예산 부족 시 제외
            
        remaining_budget = total_budget - full_meal_cost
        orders = [{"title": representative_meal['title'], "count": member_count, "unit_price": representative_meal['price']}]
        
        # [체크 2] 전원 음료(1인 1잔) 추가 가능한가?
        has_full_drinks = False
        if drinks:
            best_drink = min(drinks, key=lambda x: x['price'])
            drink_total = best_drink['price'] * member_count
            
            if drink_total <= remaining_budget:
                orders.append({
                    "title": best_drink['title'], 
                    "count": member_count, 
                    "unit_price": best_drink['price']
                })
                remaining_budget -= drink_total
                has_full_drinks = True

        # [체크 3] 추가 사이드 구성 및 풍성함 점수 계산
        side_fulfillment = 0.0 # 0.0 ~ 0.3
        if sides:
            cheapest_side = min(sides, key=lambda x: x['price'])
            # 1. 전원 사이드 가능 여부
            if cheapest_side['price'] * member_count <= remaining_budget:
                orders.append({
                    "title": cheapest_side['title'],
                    "count": member_count,
                    "unit_price": cheapest_side['price'],
                    "note": "1인 1사이드 가능"
                })
                remaining_budget -= (cheapest_side['price'] * member_count)
                side_fulfillment = 0.3
            # 2. 전원까진 아니어도 팀 공용으론 가능한지
            elif cheapest_side['price'] <= remaining_budget:
                best_shared_side = max([s for s in sides if s['price'] <= remaining_budget], key=lambda x: x['price'])
                orders.append({
                    "title": best_shared_side['title'],
                    "count": 1,
                    "unit_price": best_shared_side['price'],
                    "note": "팀 공용 사이드"
                })
                remaining_budget -= best_shared_side['price']
                side_fulfillment = 0.1

        # 4. 가점 계산 (Abundance Score)
        # 메인 기본(0.4) + 음료 전원(0.3) + 사이드 전원(0.3) = 1.0
        budget_score = 0.4
        if has_full_drinks: budget_score += 0.3
        budget_score += side_fulfillment
        
        # 5. 통합 점수 계산 (Total Score)
        # 거리 점수(50%) + 예산 점수(50%) 합산
        distance_score = restaurant.get("distance_score", 0.0)
        total_score = (distance_score * 0.5) + (budget_score * 0.5)
        
        # 6. 데이터 업데이트
        restaurant["budget_score"] = round(budget_score, 2)
        restaurant["total_score"] = round(total_score, 2)
        restaurant["budget_recommendation"] = {
            "type": "team_package",
            "message": f"인당 {total_budget // member_count}원 예산 최적화 구성",
            "menu_details": orders,
            "total_spent": total_budget - remaining_budget,
            "remaining_budget": remaining_budget
        }
        restaurant["budget_usage_pct"] = ((total_budget - remaining_budget) / total_budget) * 100
        
        _final_filtered.append(restaurant)

    # 최종 정렬: 통합 점수(거리+예산) 높은 순
    _final_filtered.sort(key=lambda x: x.get("total_score", 0), reverse=True)
    
    end_time = time()
    logger.debug("[BUDGET] 예산 및 통합 점수 필터링 소요 시간: %.4f초", end_time - start_time)
    logger.info("[BUDGET] 완료: %d개 식당 생존 (통합 정렬 적용)", len(_final_filtered))

    return {
        "filtered_restaurant": _final_filtered,
        "status_message": f"필터링 완료: {len(_final_filtered)}개 식당 정렬됨"
    }

# 메인 그래프
def get_recommend_graph():
    workflow = StateGraph(RecommendationState)

    workflow.add_node("distance", distance_node)
    # workflow.add_node("allergy", allergy_node)
    workflow.add_node("budget", budget_node)
    
    workflow.add_edge(START, "distance")
    workflow.add_edge("distance", "budget")
    workflow.add_edge("budget", END)


    return workflow.compile().with_config({"run_name": "recommend_sub_graph"})