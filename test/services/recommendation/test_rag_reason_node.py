"""rag_reason_node 단위 테스트."""
import pytest
from unittest.mock import AsyncMock, patch


def _make_processed(restaurant_id: str, approve_count: int = 0, score: float = 0.0) -> dict:
    return {
        "restaurant_id": restaurant_id,
        "place_name": f"식당_{restaurant_id}",
        "approve_count": approve_count,
        "score": score,
    }


class TestRagReasonNode:
    @pytest.mark.asyncio
    async def test_builds_final_selection_with_reasons(self):
        recommended = [_make_processed("r1"), _make_processed("r2")]
        state = {
            "dining_id": 1,
            "user_ids": [1, 2],
            "dining_data": {"budget": 50000, "dining_date": "2025-01-01"},
            "recommended_restaurants": recommended,
            "processed_restaurants": [],
        }

        reason_map = {"r1": "분위기가 좋습니다.", "r2": "가성비가 훌륭합니다."}

        with patch(
            "services.recommendation.rag_reason_node.rag_reason_task",
            new_callable=AsyncMock,
            return_value=reason_map,
        ):
            from services.recommendation.rag_reason_node import rag_reason_node
            result = await rag_reason_node(state)

        assert len(result["final_selection"]) == 2
        assert result["final_selection"][0]["restaurant_id"] == "r1"
        assert result["final_selection"][0]["reason"] == "분위기가 좋습니다."
        assert result["final_selection"][1]["reason"] == "가성비가 훌륭합니다."

    @pytest.mark.asyncio
    async def test_supplements_to_five_from_processed(self):
        """recommended가 3개면 processed에서 2개 보충."""
        recommended = [_make_processed(f"r{i}") for i in range(1, 4)]
        processed = [
            _make_processed("r4", approve_count=3, score=0.9),
            _make_processed("r5", approve_count=2, score=0.7),
            _make_processed("r6", approve_count=1, score=0.5),
        ]
        state = {
            "dining_id": 1,
            "user_ids": [1],
            "dining_data": {},
            "recommended_restaurants": recommended,
            "processed_restaurants": processed,
        }

        with patch(
            "services.recommendation.rag_reason_node.rag_reason_task",
            new_callable=AsyncMock,
            return_value={},
        ):
            from services.recommendation.rag_reason_node import rag_reason_node
            result = await rag_reason_node(state)

        ids = [r["restaurant_id"] for r in result["final_selection"]]
        assert len(ids) == 5
        # 보충은 approve_count/score 높은 순
        assert "r4" in ids
        assert "r5" in ids

    @pytest.mark.asyncio
    async def test_fallback_reason_when_rag_fails(self):
        """rag_reason_task 실패 시 generic fallback 사용."""
        state = {
            "dining_id": 1,
            "user_ids": [1],
            "dining_data": {},
            "recommended_restaurants": [_make_processed("r1")],
            "processed_restaurants": [],
        }

        with patch(
            "services.recommendation.rag_reason_node.rag_reason_task",
            new_callable=AsyncMock,
            side_effect=Exception("Qdrant 연결 실패"),
        ):
            from services.recommendation.rag_reason_node import rag_reason_node
            result = await rag_reason_node(state)

        assert len(result["final_selection"]) == 1
        assert result["final_selection"][0]["reason"] == "예산과 위치를 고려한 최적의 회식 장소입니다."

    @pytest.mark.asyncio
    async def test_empty_candidates_returns_empty_selection(self):
        state = {
            "dining_id": 1,
            "user_ids": [],
            "dining_data": {},
            "recommended_restaurants": [],
            "processed_restaurants": [],
        }

        from services.recommendation.rag_reason_node import rag_reason_node
        result = await rag_reason_node(state)

        assert result["final_selection"] == []

    @pytest.mark.asyncio
    async def test_caps_at_five(self):
        """recommended가 6개여도 5개만 선택."""
        recommended = [_make_processed(f"r{i}") for i in range(1, 7)]
        state = {
            "dining_id": 1,
            "user_ids": [1],
            "dining_data": {},
            "recommended_restaurants": recommended,
            "processed_restaurants": [],
        }

        with patch(
            "services.recommendation.rag_reason_node.rag_reason_task",
            new_callable=AsyncMock,
            return_value={},
        ):
            from services.recommendation.rag_reason_node import rag_reason_node
            result = await rag_reason_node(state)

        assert len(result["final_selection"]) == 5
