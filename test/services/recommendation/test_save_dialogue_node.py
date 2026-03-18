"""save_dialogue_node 단위 테스트."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSaveDialogueNode:
    @pytest.mark.asyncio
    async def test_saves_dialogue_history(self):
        dialogue = [
            {"type": "analyst", "restaurant_id": "r1", "content": "좋은 식당입니다."},
            {"type": "vote", "user_id": 1, "restaurant_id": "r1", "approve": True},
        ]
        state = {"dining_id": 10, "dialogue_history": dialogue}

        mock_db = MagicMock()
        mock_db.update_one_with_command = AsyncMock(return_value=1)

        with patch(
            "services.recommendation.save_dialogue_node.DBManager", return_value=mock_db
        ):
            from services.recommendation.save_dialogue_node import save_dialogue_node
            result = await save_dialogue_node(state)

        mock_db.update_one_with_command.assert_called_once()
        call_args = mock_db.update_one_with_command.call_args
        assert call_args[0][0] == {"diningId": 10}
        assert "$set" in call_args[0][1]
        assert call_args[0][1]["$set"]["dialogueHistory"] == dialogue
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_db_failure(self):
        """DB 실패해도 {} 반환하여 파이프라인 계속."""
        state = {"dining_id": 1, "dialogue_history": [{"type": "analyst"}]}

        mock_db = MagicMock()
        mock_db.update_one_with_command = AsyncMock(side_effect=Exception("timeout"))

        with patch(
            "services.recommendation.save_dialogue_node.DBManager", return_value=mock_db
        ):
            from services.recommendation.save_dialogue_node import save_dialogue_node
            result = await save_dialogue_node(state)

        assert result == {}

    @pytest.mark.asyncio
    async def test_empty_dialogue_history(self):
        state = {"dining_id": 5, "dialogue_history": []}

        mock_db = MagicMock()
        mock_db.update_one_with_command = AsyncMock(return_value=1)

        with patch(
            "services.recommendation.save_dialogue_node.DBManager", return_value=mock_db
        ):
            from services.recommendation.save_dialogue_node import save_dialogue_node
            result = await save_dialogue_node(state)

        assert result == {}
