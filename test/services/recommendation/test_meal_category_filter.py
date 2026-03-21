"""TDD: services/recommendation/sub_graphs/meal_category_filter.py 단위 테스트."""
import pytest


# ─── _is_non_meal ─────────────────────────────────────────────────────────────


class TestIsNonMeal:
    def _fn(self):
        from services.recommendation.sub_graphs.meal_category_filter import _is_non_meal
        return _is_non_meal

    def test_cafe_is_non_meal(self):
        assert self._fn()({"category_detail": "카페 > 커피전문점"}) is True

    def test_bakery_is_non_meal(self):
        assert self._fn()({"category_detail": "베이커리"}) is True

    def test_korean_food_passes(self):
        assert self._fn()({"category_detail": "한식 > 백반/한정식"}) is False

    def test_empty_category_passes(self):
        assert self._fn()({"category_detail": ""}) is False

    def test_none_category_passes(self):
        assert self._fn()({"category_detail": None}) is False

    def test_missing_key_passes(self):
        assert self._fn()({}) is False

    @pytest.mark.parametrize("keyword", [
        "카페", "커피", "베이커리", "빵", "디저트",
        "아이스크림", "빙수", "주스", "티하우스", "찻집", "테이크아웃",
    ])
    def test_all_blocked_keywords(self, keyword: str):
        assert self._fn()({"category_detail": keyword}) is True


# ─── meal_category_filter_node ────────────────────────────────────────────────


class TestMealCategoryFilterNode:
    @pytest.mark.asyncio
    async def test_removes_non_meal_restaurants(self):
        from services.recommendation.sub_graphs.meal_category_filter import meal_category_filter_node

        state = {
            "filtered_restaurant": [
                {"place_name": "스타벅스", "category_detail": "카페 > 커피전문점"},
                {"place_name": "파리바게뜨", "category_detail": "베이커리"},
                {"place_name": "한식당", "category_detail": "한식 > 백반/한정식"},
            ]
        }
        result = await meal_category_filter_node(state)

        names = [r["place_name"] for r in result["filtered_restaurant"]]
        assert names == ["한식당"]

    @pytest.mark.asyncio
    async def test_no_category_passes_through(self):
        from services.recommendation.sub_graphs.meal_category_filter import meal_category_filter_node

        state = {
            "filtered_restaurant": [
                {"place_name": "미분류식당", "category_detail": ""},
                {"place_name": "키없는식당"},
            ]
        }
        result = await meal_category_filter_node(state)
        assert len(result["filtered_restaurant"]) == 2

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self):
        from services.recommendation.sub_graphs.meal_category_filter import meal_category_filter_node

        result = await meal_category_filter_node({"filtered_restaurant": []})
        assert result["filtered_restaurant"] == []

    @pytest.mark.asyncio
    async def test_status_message_contains_counts(self):
        from services.recommendation.sub_graphs.meal_category_filter import meal_category_filter_node

        state = {
            "filtered_restaurant": [
                {"place_name": "카페A", "category_detail": "카페"},
                {"place_name": "한식당", "category_detail": "한식"},
            ]
        }
        result = await meal_category_filter_node(state)
        msg = result["status_message"]
        assert "1개 제외" in msg
        assert "1개 통과" in msg
