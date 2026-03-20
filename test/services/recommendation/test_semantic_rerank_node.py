"""TDD: services/recommendation/semantic_rerank_node.py 단위 테스트."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def make_restaurant(
    rid: str = "r1",
    total_score: float = 0.8,
    allergy_penalty: float = 0.0,
) -> dict:
    return {
        "_id": rid,
        "place_name": f"식당_{rid}",
        "total_score": total_score,
        "allergy_penalty": allergy_penalty,
    }


def make_state(
    user_ids: list[int] | None = None,
    restaurants: list[dict] | None = None,
) -> dict:
    return {
        "user_ids": user_ids if user_ids is not None else [1],
        "filtered_restaurant": restaurants if restaurants is not None else [make_restaurant()],
        "status_message": [],
        "dining_data": {},
        "dining_id": "d1",
    }


# ─── 빈 입력 처리 ─────────────────────────────────────────────────────────────

class TestEmptyInput:
    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_no_restaurants(self):
        """filtered_restaurant가 비어있으면 빈 dict를 반환하는지."""
        from services.recommendation.semantic_rerank_node import semantic_rerank_node

        state = make_state(restaurants=[])
        result = await semantic_rerank_node(state)
        assert result == {}


# ─── basePersona 없는 경우 ────────────────────────────────────────────────────

class TestNoPersona:
    @pytest.mark.asyncio
    async def test_maintains_total_score_order_when_no_persona(self):
        """basePersona가 없는 유저면 total_score 기준 정렬을 유지하는지."""
        from services.recommendation.semantic_rerank_node import semantic_rerank_node

        restaurants = [
            make_restaurant("r1", total_score=0.5),
            make_restaurant("r2", total_score=0.9),
            make_restaurant("r3", total_score=0.7),
        ]
        state = make_state(user_ids=[1], restaurants=restaurants)

        with patch(
            "services.recommendation.semantic_rerank_node.DBManager"
        ) as MockDB:
            mock_db = MagicMock()
            # basePersona 없는 유저
            mock_db.read_one = AsyncMock(return_value={"id": 1})
            MockDB.return_value = mock_db

            result = await semantic_rerank_node(state)

        filtered = result.get("filtered_restaurant", [])
        scores = [r["final_score"] for r in filtered]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_still_returns_filtered_restaurant_when_no_persona(self):
        """basePersona가 없어도 filtered_restaurant가 반환되는지."""
        from services.recommendation.semantic_rerank_node import semantic_rerank_node

        state = make_state(restaurants=[make_restaurant("r1")])

        with patch(
            "services.recommendation.semantic_rerank_node.DBManager"
        ) as MockDB:
            mock_db = MagicMock()
            mock_db.read_one = AsyncMock(return_value={"id": 1})
            MockDB.return_value = mock_db

            result = await semantic_rerank_node(state)

        assert "filtered_restaurant" in result
        assert len(result["filtered_restaurant"]) == 1


# ─── final_score 계산 공식 ────────────────────────────────────────────────────

class TestFinalScoreFormula:
    @pytest.mark.asyncio
    async def test_final_score_formula_with_semantic(self):
        """final_score = total×0.4 + semantic×0.4 - penalty×0.2 공식이 맞는지."""
        from services.recommendation.semantic_rerank_node import semantic_rerank_node

        restaurant = make_restaurant("r1", total_score=0.8, allergy_penalty=0.1)
        state = make_state(user_ids=[1], restaurants=[restaurant])

        with patch(
            "services.recommendation.semantic_rerank_node.DBManager"
        ) as MockDB, patch(
            "services.recommendation.semantic_rerank_node._fetch_semantic_scores",
            new_callable=AsyncMock,
        ) as mock_fetch, patch(
            "services.recommendation.semantic_rerank_node._get_embedding",
            new_callable=AsyncMock,
        ) as mock_embed:
            mock_db = MagicMock()
            mock_db.read_one = AsyncMock(
                return_value={"id": 1, "basePersona": "한식을 좋아하는 30대"}
            )
            MockDB.return_value = mock_db
            mock_embed.return_value = [0.1] * 1536
            mock_fetch.return_value = {"r1": 0.6}

            result = await semantic_rerank_node(state)

        filtered = result.get("filtered_restaurant", [])
        assert len(filtered) == 1
        r = filtered[0]
        expected = 0.8 * 0.4 + 0.6 * 0.4 - 0.1 * 0.2
        assert r["final_score"] == pytest.approx(expected, abs=0.001)

    @pytest.mark.asyncio
    async def test_final_score_without_semantic(self):
        """semantic_score=0 시 final_score = total×0.4 - penalty×0.2인지."""
        from services.recommendation.semantic_rerank_node import semantic_rerank_node

        restaurant = make_restaurant("r1", total_score=0.8, allergy_penalty=0.1)
        state = make_state(user_ids=[1], restaurants=[restaurant])

        with patch(
            "services.recommendation.semantic_rerank_node.DBManager"
        ) as MockDB:
            mock_db = MagicMock()
            mock_db.read_one = AsyncMock(return_value={"id": 1})  # no basePersona
            MockDB.return_value = mock_db

            result = await semantic_rerank_node(state)

        filtered = result.get("filtered_restaurant", [])
        r = filtered[0]
        expected = 0.8 * 0.4 - 0.1 * 0.2
        assert r["final_score"] == pytest.approx(expected, abs=0.001)

    @pytest.mark.asyncio
    async def test_sorted_by_final_score_descending(self):
        """재정렬 후 final_score 내림차순 정렬이 맞는지."""
        from services.recommendation.semantic_rerank_node import semantic_rerank_node

        restaurants = [
            make_restaurant("r1", total_score=0.5),
            make_restaurant("r2", total_score=0.9),
            make_restaurant("r3", total_score=0.3),
        ]
        state = make_state(user_ids=[1], restaurants=restaurants)

        with patch(
            "services.recommendation.semantic_rerank_node.DBManager"
        ) as MockDB, patch(
            "services.recommendation.semantic_rerank_node._fetch_semantic_scores",
            new_callable=AsyncMock,
        ) as mock_fetch, patch(
            "services.recommendation.semantic_rerank_node._get_embedding",
            new_callable=AsyncMock,
        ) as mock_embed:
            mock_db = MagicMock()
            mock_db.read_one = AsyncMock(
                return_value={"id": 1, "basePersona": "persona"}
            )
            MockDB.return_value = mock_db
            mock_embed.return_value = [0.1] * 1536
            mock_fetch.return_value = {"r1": 0.3, "r2": 0.7, "r3": 0.1}

            result = await semantic_rerank_node(state)

        filtered = result.get("filtered_restaurant", [])
        scores = [r["final_score"] for r in filtered]
        assert scores == sorted(scores, reverse=True)


# ─── Neo4j 오류 시 graceful fallback ─────────────────────────────────────────

class TestGracefulFallback:
    @pytest.mark.asyncio
    async def test_no_exception_on_neo4j_error(self):
        """Neo4j 오류 시 예외 없이 통과하는지."""
        from services.recommendation.semantic_rerank_node import semantic_rerank_node

        state = make_state(restaurants=[make_restaurant("r1", total_score=0.8)])

        with patch(
            "services.recommendation.semantic_rerank_node.DBManager"
        ) as MockDB, patch(
            "services.recommendation.semantic_rerank_node._get_embedding",
            new_callable=AsyncMock,
        ) as mock_embed, patch(
            "services.recommendation.semantic_rerank_node._fetch_semantic_scores",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_db = MagicMock()
            mock_db.read_one = AsyncMock(
                return_value={"id": 1, "basePersona": "persona"}
            )
            MockDB.return_value = mock_db
            mock_embed.return_value = [0.1] * 1536
            mock_fetch.side_effect = Exception("Neo4j connection refused")

            # 예외 없이 실행되어야 함
            result = await semantic_rerank_node(state)

        assert "filtered_restaurant" in result

    @pytest.mark.asyncio
    async def test_returns_restaurants_on_neo4j_error(self):
        """Neo4j 오류 시에도 filtered_restaurant가 반환되는지."""
        from services.recommendation.semantic_rerank_node import semantic_rerank_node

        state = make_state(restaurants=[make_restaurant("r1"), make_restaurant("r2")])

        with patch(
            "services.recommendation.semantic_rerank_node.DBManager"
        ) as MockDB, patch(
            "services.recommendation.semantic_rerank_node._get_embedding",
            new_callable=AsyncMock,
        ) as mock_embed, patch(
            "services.recommendation.semantic_rerank_node._fetch_semantic_scores",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_db = MagicMock()
            mock_db.read_one = AsyncMock(
                return_value={"id": 1, "basePersona": "persona"}
            )
            MockDB.return_value = mock_db
            mock_embed.return_value = [0.1] * 1536
            mock_fetch.side_effect = Exception("Neo4j error")

            result = await semantic_rerank_node(state)

        assert len(result.get("filtered_restaurant", [])) == 2
