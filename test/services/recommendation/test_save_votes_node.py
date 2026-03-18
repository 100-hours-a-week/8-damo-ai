"""save_votes_node 단위 테스트."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSaveVotesNode:
    @pytest.mark.asyncio
    async def test_saves_persona_votes(self):
        state = {
            "dining_id": 42,
            "persona_votes": [
                {"user_id": 1, "restaurant_id": "r1", "approve": True},
                {"user_id": 2, "restaurant_id": "r1", "approve": False},
            ],
        }

        mock_db = MagicMock()
        mock_db.update_one_with_command = AsyncMock(return_value=1)

        with patch(
            "services.recommendation.save_votes_node.DBManager", return_value=mock_db
        ):
            from services.recommendation.save_votes_node import save_votes_node
            result = await save_votes_node(state)

        mock_db.update_one_with_command.assert_called_once()
        call_args = mock_db.update_one_with_command.call_args
        assert call_args[0][0] == {"diningId": 42}
        assert "$push" in call_args[0][1]
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_db_failure(self):
        """DB 실패해도 {} 반환하여 파이프라인 계속."""
        state = {"dining_id": 1, "persona_votes": [{"user_id": 1}]}

        mock_db = MagicMock()
        mock_db.update_one_with_command = AsyncMock(side_effect=Exception("DB 연결 실패"))

        with patch(
            "services.recommendation.save_votes_node.DBManager", return_value=mock_db
        ):
            from services.recommendation.save_votes_node import save_votes_node
            result = await save_votes_node(state)

        assert result == {}

    @pytest.mark.asyncio
    async def test_empty_persona_votes(self):
        state = {"dining_id": 1, "persona_votes": []}

        mock_db = MagicMock()
        mock_db.update_one_with_command = AsyncMock(return_value=1)

        with patch(
            "services.recommendation.save_votes_node.DBManager", return_value=mock_db
        ):
            from services.recommendation.save_votes_node import save_votes_node
            result = await save_votes_node(state)

        assert result == {}
