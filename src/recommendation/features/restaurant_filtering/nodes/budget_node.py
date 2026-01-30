from src.shared.db.db_manager import MongoManager
from src.recommendation.workflows.states.recommendation_state import RecommendationState
from time import time

async def budget_node(state: RecommendationState) -> dict:
    start_time = time()
    total_budget = getattr(state["dining_data"], "budget", 0) 
    member_count = len(state["user_ids"])
    
    if total_budget <= 0 or member_count <= 0:
        return {"status_message": "예산 정보 부족으로 필터링을 스킵합니다."}

    _final_filtered = []
    # 주류 및 음료 키워드
    DRINK_KEYWORDS = ["소주", "맥주", "음료", "콜라", "사이다", "주류", "와인", "에이드", "커피", "티", "주스", "환타", "동동주", "막걸리", "하이볼"]

    for restaurant in state["filtered_restaurants"]:
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
    print(f"예산 및 통합 점수 필터링 완료: {len(_final_filtered)}개 식당 생존 (통합 정렬 적용)")
    print(f"예산 및 통합 점수 필터링 소요 시간: {end_time - start_time:.4f}초")

    return {
        "filtered_restaurants": _final_filtered,
        "status_message": f"필터링 완료: {len(_final_filtered)}개 식당 정렬됨"
    }