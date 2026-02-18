from typing import Any, Dict, List


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
    """식당 카테고리와 그룹 선호도 겹침 점수 (0.0 ~ 1.0)."""
    if total_users == 0:
        return 0.0

    category = restaurant.get("category_detail", "")
    if not category:
        return 0.0

    match_count = group_preferences.get(category, 0)
    return match_count / total_users


def rank_restaurants(
    restaurants: List[Dict[str, Any]],
    user_data_list: List[Dict[str, Any]],
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """그룹 선호도 점수로 식당을 정렬하고 Top K 반환.

    알레르기 필터링은 이미 사전에 완료된 상태로 전달됨.
    각 식당 dict에 'score' 필드를 추가하여 반환.
    """
    total_users = len(user_data_list)
    group_preferences = aggregate_group_preferences(user_data_list)

    scored: List[Dict[str, Any]] = []
    for r in restaurants:
        score = compute_category_overlap_score(r, group_preferences, total_users)
        entry = {**r, "score": round(score, 4)}
        scored.append(entry)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
