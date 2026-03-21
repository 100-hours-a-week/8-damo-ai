"""비식사 장소(카페, 베이커리, 디저트 등) 카테고리 필터 노드."""

from __future__ import annotations

from services.recommendation.state import PipelineState

NON_MEAL_CATEGORIES: frozenset[str] = frozenset({
    "카페", "커피", "베이커리", "빵", "디저트",
    "아이스크림", "빙수", "주스", "티하우스", "찻집", "테이크아웃",
})


def _is_non_meal(restaurant: dict) -> bool:
    category = (restaurant.get("category_detail") or "").strip()
    if not category:
        return False  # category 없으면 통과
    return any(kw in category for kw in NON_MEAL_CATEGORIES)


async def meal_category_filter_node(state: PipelineState) -> dict:
    restaurants = state.get("filtered_restaurant", [])
    filtered = [r for r in restaurants if not _is_non_meal(r)]
    excluded = len(restaurants) - len(filtered)
    return {
        "filtered_restaurant": filtered,
        "status_message": f"카테고리 필터링 완료: {excluded}개 제외, {len(filtered)}개 통과",
    }
