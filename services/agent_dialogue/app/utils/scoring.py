import math
from typing import Any, Dict, List, Optional


def aggregate_group_preferences(
    user_data_list: List[Dict[str, Any]],
) -> Dict[str, int]:
    """그룹 유저들의 선호 카테고리를 집계하여 카테고리별 선호 인원수를 반환."""
    category_counts: Dict[str, int] = {}
    for user in user_data_list:
        like_cats = (
            user.get("like_food_categories_id")
            or user.get("likeFoodCategoriesId")
            or []
        )
        for cat in like_cats:
            category_counts[cat] = category_counts.get(cat, 0) + 1
    return category_counts


def compute_category_overlap_score(
    restaurant: Dict[str, Any],
    group_preferences: Dict[str, int],
    total_users: int,
) -> float:
    """식당 카테고리와 그룹 선호도 겹침 점수 (0.0 ~ 1.0).

    부분 매칭 사용: "한식 > 삼겹살"은 "한식" 선호 유저와 매칭됨.
    """
    if total_users == 0:
        return 0.0

    category = restaurant.get("category_detail", "")
    if not category:
        return 0.0

    match_count = 0
    for cat, count in group_preferences.items():
        if cat in category:
            match_count += count
    return min(match_count / total_users, 1.0)


def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 간 Haversine 거리 반환 (미터)."""
    R = 6_371_000  # 지구 반지름 (m)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def compute_distance_score(
    restaurant: Dict[str, Any],
    dining_data: Dict[str, Any],
) -> float:
    """가까울수록 1.0, 멀수록 0.0 (2km 기준)."""
    MAX_DIST = 2000  # m
    try:
        coords = restaurant.get("location", {}).get("coordinates", [])
        if len(coords) < 2:
            return 0.0
        rest_lng, rest_lat = float(coords[0]), float(coords[1])
        ref_lng = float(dining_data.get("x", 0) or 0)
        ref_lat = float(dining_data.get("y", 0) or 0)
        if ref_lng == 0 and ref_lat == 0:
            return 0.0
        dist = _haversine_distance(ref_lat, ref_lng, rest_lat, rest_lng)
        return max(0.0, 1.0 - dist / MAX_DIST)
    except (TypeError, ValueError):
        return 0.0


def compute_review_score(restaurant: Dict[str, Any]) -> float:
    """리뷰 100개 기준 0~1 정규화 (루트 스케일)."""
    count = restaurant.get("review_count") or restaurant.get("reviewCount") or 0
    return min(count / 100, 1.0) ** 0.5


def rank_restaurants(
    restaurants: List[Dict[str, Any]],
    user_data_list: List[Dict[str, Any]],
    dining_data: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """그룹 선호도 점수로 식당을 정렬하고 Top K 반환.

    알레르기 필터링은 이미 사전에 완료된 상태로 전달됨.
    각 식당 dict에 'score' 필드를 추가하여 반환.
    """
    total_users = len(user_data_list)
    group_preferences = aggregate_group_preferences(user_data_list)

    scored: List[Dict[str, Any]] = []
    for r in restaurants:
        category_score = compute_category_overlap_score(r, group_preferences, total_users)
        distance_score = compute_distance_score(r, dining_data) if dining_data else 0.0
        review_score = compute_review_score(r)

        score = (
            category_score * 0.6
            + distance_score * 0.3
            + review_score * 0.1
        )
        entry = {**r, "score": round(score, 4)}
        scored.append(entry)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
