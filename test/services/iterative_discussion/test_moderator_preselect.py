"""Node 2: Moderator Pre-Selection 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.iterative_discussion.app.nodes.moderator_preselect import (
    moderator_preselect,
)
from services.iterative_discussion.app.utils.scoring import (
    aggregate_group_preferences,
    compute_category_overlap_score,
    rank_restaurants,
)


class TestAggregateGroupPreferences:
    def test_basic_count(self, sample_user_data_list) -> None:
        result = aggregate_group_preferences(sample_user_data_list)
        assert result["한식"] == 2  # 철수 + 민수
        assert result["일식"] == 2  # 철수 + 영희
        assert result["양식"] == 1  # 영희

    def test_empty_users(self) -> None:
        assert aggregate_group_preferences([]) == {}

    def test_no_preferences(self) -> None:
        users = [{"like_food_categories_id": []}]
        assert aggregate_group_preferences(users) == {}


class TestComputeCategoryOverlapScore:
    def test_full_match(self) -> None:
        restaurant = {"category_detail": "한식"}
        prefs = {"한식": 3}
        assert compute_category_overlap_score(restaurant, prefs, 3) == 1.0

    def test_partial_match(self) -> None:
        restaurant = {"category_detail": "한식"}
        prefs = {"한식": 1}
        score = compute_category_overlap_score(restaurant, prefs, 3)
        assert abs(score - 1 / 3) < 0.01

    def test_no_match(self) -> None:
        restaurant = {"category_detail": "멕시칸"}
        prefs = {"한식": 2}
        assert compute_category_overlap_score(restaurant, prefs, 2) == 0.0

    def test_empty_category(self) -> None:
        restaurant = {"category_detail": ""}
        assert compute_category_overlap_score(restaurant, {"한식": 1}, 1) == 0.0

    def test_zero_users(self) -> None:
        restaurant = {"category_detail": "한식"}
        assert compute_category_overlap_score(restaurant, {"한식": 1}, 0) == 0.0


class TestRankRestaurants:
    def test_top_k_selection(
        self, sample_restaurant_docs, sample_user_data_list
    ) -> None:
        result = rank_restaurants(
            sample_restaurant_docs, sample_user_data_list, top_k=5
        )
        assert len(result) == 5
        assert all("score" in r for r in result)

    def test_sorted_by_score(
        self, sample_restaurant_docs, sample_user_data_list
    ) -> None:
        result = rank_restaurants(
            sample_restaurant_docs, sample_user_data_list, top_k=10
        )
        scores = [r["score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_top_categories(
        self, sample_restaurant_docs, sample_user_data_list
    ) -> None:
        result = rank_restaurants(
            sample_restaurant_docs, sample_user_data_list, top_k=3
        )
        top_categories = {r["category_detail"] for r in result}
        # 한식(2명) + 일식(2명)이 상위, 양식(1명)과 중식(0명)은 하위
        assert "한식" in top_categories or "일식" in top_categories

    def test_empty_restaurants(self, sample_user_data_list) -> None:
        result = rank_restaurants([], sample_user_data_list, top_k=10)
        assert result == []

    def test_fewer_than_top_k(self, sample_user_data_list) -> None:
        restaurants = [
            {"_id": "r1", "place_name": "A", "category_detail": "한식"},
        ]
        result = rank_restaurants(restaurants, sample_user_data_list, top_k=10)
        assert len(result) == 1


@pytest.mark.asyncio
class TestModeratorPreselect:
    async def test_empty_restaurant_ids(self, sample_user_data_list) -> None:
        state = {
            "filtered_restaurant_ids": [],
            "user_data_list": sample_user_data_list,
        }
        result = await moderator_preselect(state)
        assert result["is_error"] is True
        assert "filtered_restaurant_ids" in result["error_message"]

    async def test_empty_user_data(self) -> None:
        state = {
            "filtered_restaurant_ids": ["r1"],
            "user_data_list": [],
        }
        result = await moderator_preselect(state)
        assert result["is_error"] is True
        assert "user_data_list" in result["error_message"]

    async def test_successful_preselection(
        self, sample_restaurant_docs, sample_user_data_list, sample_restaurant_ids
    ) -> None:
        restaurant_map = {r["_id"]: r for r in sample_restaurant_docs}

        async def _read_all(query):
            ids = query.get("_id", {}).get("$in", [])
            return [dict(restaurant_map[rid]) for rid in ids if rid in restaurant_map]

        mock_db = MagicMock()
        mock_db.read_all = AsyncMock(side_effect=_read_all)

        with patch(
            "services.iterative_discussion.app.nodes.moderator_preselect.DBManager",
            return_value=mock_db,
        ), patch(
            "services.iterative_discussion.app.nodes.moderator_preselect.ObjectId",
            side_effect=lambda x: x,
        ):
            state = {
                "filtered_restaurant_ids": sample_restaurant_ids,
                "user_data_list": sample_user_data_list,
            }
            result = await moderator_preselect(state)

            assert "is_error" not in result
            assert len(result["candidate_pool"]) == 10
            assert all("score" in r for r in result["candidate_pool"])

    async def test_rejected_restaurants_excluded(
        self, sample_restaurant_docs, sample_user_data_list, sample_restaurant_ids
    ) -> None:
        """rejected_restaurant_ids에 포함된 식당은 candidate_pool에서 제외된다."""
        restaurant_map = {r["_id"]: r for r in sample_restaurant_docs}

        async def _read_all(query):
            ids = query.get("_id", {}).get("$in", [])
            return [dict(restaurant_map[rid]) for rid in ids if rid in restaurant_map]

        mock_db = MagicMock()
        mock_db.read_all = AsyncMock(side_effect=_read_all)

        with patch(
            "services.iterative_discussion.app.nodes.moderator_preselect.DBManager",
            return_value=mock_db,
        ), patch(
            "services.iterative_discussion.app.nodes.moderator_preselect.ObjectId",
            side_effect=lambda x: x,
        ):
            state = {
                "filtered_restaurant_ids": sample_restaurant_ids,
                "user_data_list": sample_user_data_list,
                "rejected_restaurant_ids": ["r1", "r4"],
            }
            result = await moderator_preselect(state)

            assert "is_error" not in result
            candidate_ids = [str(r.get("_id", "")) for r in result["candidate_pool"]]
            assert "r1" not in candidate_ids
            assert "r4" not in candidate_ids
            # rejected_restaurant_ids가 초기화되었는지 확인
            assert result["rejected_restaurant_ids"] == []

    async def test_db_returns_no_restaurants(
        self, sample_user_data_list
    ) -> None:
        mock_db = MagicMock()
        mock_db.read_all = AsyncMock(return_value=[])

        with patch(
            "services.iterative_discussion.app.nodes.moderator_preselect.DBManager",
            return_value=mock_db,
        ), patch(
            "services.iterative_discussion.app.nodes.moderator_preselect.ObjectId",
            side_effect=lambda x: x,
        ):
            state = {
                "filtered_restaurant_ids": ["nonexistent"],
                "user_data_list": sample_user_data_list,
            }
            result = await moderator_preselect(state)
            assert result["is_error"] is True
