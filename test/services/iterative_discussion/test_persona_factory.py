"""Node 1: Persona Factory 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.iterative_discussion.app.nodes.persona_factory import (
    _build_persona_prompt,
    persona_factory,
)


class TestBuildPersonaPrompt:
    def test_with_base_persona(self) -> None:
        user = {
            "nickname": "철수",
            "basePersona": "20대 남성, 매운 음식을 좋아하고 한식과 일식을 선호합니다.",
            "allergies": ["땅콩"],
        }
        prompt = _build_persona_prompt(user)
        assert "철수" in prompt
        assert "20대 남성" in prompt
        assert "땅콩" in prompt

    def test_base_persona_snake_case_key(self) -> None:
        user = {
            "nickname": "영희",
            "base_persona": "30대 여성, 양식을 좋아합니다.",
            "allergies": [],
        }
        prompt = _build_persona_prompt(user)
        assert "30대 여성" in prompt
        assert "없음" in prompt  # 알레르기 없음

    def test_missing_base_persona_fallback(self) -> None:
        user = {
            "nickname": "민수",
            "allergies": ["갑각류"],
        }
        prompt = _build_persona_prompt(user)
        assert "정보 없음" in prompt
        assert "갑각류" in prompt

    def test_empty_allergies(self) -> None:
        user = {
            "nickname": "영희",
            "basePersona": "일식 선호",
            "allergies": [],
        }
        prompt = _build_persona_prompt(user)
        assert "없음" in prompt

    def test_missing_nickname_fallback(self) -> None:
        user = {
            "basePersona": "한식 좋아함",
            "allergies": [],
        }
        prompt = _build_persona_prompt(user)
        assert "익명" in prompt


@pytest.mark.asyncio
class TestPersonaFactory:
    async def test_empty_user_ids(self) -> None:
        state = {"user_ids": [], "dining_data": {}}
        result = await persona_factory(state)
        assert result["is_error"] is True
        assert "user_ids" in result["error_message"]

    async def test_users_not_found_in_db(self) -> None:
        mock_db = MagicMock()
        mock_db.read_one = AsyncMock(return_value=None)

        with patch(
            "services.iterative_discussion.app.nodes.persona_factory.DBManager",
            return_value=mock_db,
        ):
            state = {"user_ids": [999], "dining_data": {}}
            result = await persona_factory(state)
            assert result["is_error"] is True
            assert "찾을 수 없습니다" in result["error_message"]

    async def test_successful_prompt_generation(
        self, sample_user_data_list
    ) -> None:
        user_map = {u["id"]: u for u in sample_user_data_list}

        async def _read_one(query):
            return user_map.get(query.get("id"))

        mock_db = MagicMock()
        mock_db.read_one = AsyncMock(side_effect=_read_one)

        with patch(
            "services.iterative_discussion.app.nodes.persona_factory.DBManager",
            return_value=mock_db,
        ):
            state = {"user_ids": [1, 2, 3], "dining_data": {}}
            result = await persona_factory(state)

            assert "is_error" not in result
            assert len(result["user_data_list"]) == 3
            assert len(result["persona_prompts"]) == 3
            assert "1" in result["persona_prompts"]
            assert "2" in result["persona_prompts"]
            assert "3" in result["persona_prompts"]

    async def test_base_persona_reflected_in_prompt(
        self, sample_user_data_list
    ) -> None:
        user_map = {u["id"]: u for u in sample_user_data_list}

        async def _read_one(query):
            return user_map.get(query.get("id"))

        mock_db = MagicMock()
        mock_db.read_one = AsyncMock(side_effect=_read_one)

        with patch(
            "services.iterative_discussion.app.nodes.persona_factory.DBManager",
            return_value=mock_db,
        ):
            state = {"user_ids": [1], "dining_data": {}}
            result = await persona_factory(state)

            prompt_1 = result["persona_prompts"]["1"]
            assert "매운 음식을 좋아하는 20대 남성" in prompt_1
