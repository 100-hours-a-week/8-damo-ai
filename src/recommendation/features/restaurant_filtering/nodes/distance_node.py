from src.shared.db.db_manager import MongoManager
from src.recommendation.workflows.states.recommendation_state import RecommendationState
from time import time

async def distance_node(state: RecommendationState) -> RecommendationState:
    start_time = time()
    mongo = MongoManager()
    mongo.set_collection("restaurants")
    _X = float(state["dining_data"].x)
    _Y = float(state["dining_data"].y)
    MAX_DISTANCE = 1000 # 1km

    # 1. 거리 가까운 식당 가져오기
    restaurants = await mongo.find_by_location(_X, _Y, MAX_DISTANCE)
    
    if not restaurants or len(restaurants) == 0:
        return {
            "filtered_restaurants": [],
            "status_message": "필터링된 식당이 없습니다",
            "is_error": True,
            "error_message": "No restaurants found"
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

    end_time = time()
    print(f"거리 필터링 완료: {len(restaurants)}개 검색됨 (가까운 순 정렬)")
    print(f"거리 필터링 소요 시간: {end_time - start_time:.4f}초")
    return {
        "filtered_restaurants": restaurants,
        "status_message": f"거리 필터링 완료: {len(restaurants)}개 검색됨 (가까운 순 정렬)"
    }