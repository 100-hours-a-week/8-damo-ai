"""Node 1: Persona Factory 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.iterative_discussion.app.nodes.persona_factory import (
    _build_persona_prompt,
    _extract_insights,
    _strip_insights,
    persona_factory,
)


class TestExtractInsights:
    def test_single_insight(self) -> None:
        text = "[System Insight] 일식을 거부하는 경향"
        assert _extract_insights(text) == ["일식을 거부하는 경향"]

    def test_multiple_insights(self) -> None:
        text = (
            "[System Insight] 매운 음식 선호\n"
            "기타 특이사항\n"
            "[System Insight] 가격에 민감"
        )
        result = _extract_insights(text)
        assert len(result) == 2
        assert "매운 음식 선호" in result
        assert "가격에 민감" in result

    def test_no_insights(self) -> None:
        assert _extract_insights("그냥 평범한 특이사항") == []

    def test_empty_string(self) -> None:
        assert _extract_insights("") == []


class TestStripInsights:
    def test_strip_single(self) -> None:
        text = "매운 음식 좋아함\n[System Insight] 일식 거부"
        result = _strip_insights(text)
        assert "[System Insight]" not in result
        assert "매운 음식 좋아함" in result

    def test_strip_preserves_original(self) -> None:
        text = "특이사항 없음"
        assert _strip_insights(text) == "특이사항 없음"


class TestBuildPersonaPrompt:
    def test_cold_start(self) -> None:
        user = {
            "nickname": "철수",
            "gender": "남성",
            "age_group": "20대",
            "allergies": ["땅콩"],
            "like_food_categories_id": ["한식", "일식"],
            "categories_id": ["한식", "일식"],
            "other_characteristics": "매운 음식 좋아함",
        }
        prompt = _build_persona_prompt(user)
        assert "철수" in prompt
        assert "남성" in prompt
        assert "땅콩" in prompt
        assert "한식" in prompt
        assert "매운 음식 좋아함" in prompt
        assert "시스템 인사이트" not in prompt

    def test_with_system_insight(self) -> None:
        user = {
            "nickname": "민수",
            "gender": "남성",
            "age_group": "20대",
            "allergies": [],
            "like_food_categories_id": ["한식"],
            "categories_id": ["한식"],
            "other_characteristics": "평소 특이사항\n[System Insight] 일식을 거부함",
        }
        prompt = _build_persona_prompt(user)
        assert "시스템 인사이트" in prompt
        assert "일식을 거부함" in prompt

    def test_empty_allergies(self) -> None:
        user = {
            "nickname": "영희",
            "gender": "여성",
            "age_group": "30대",
            "allergies": [],
            "like_food_categories_id": [],
            "categories_id": [],
            "other_characteristics": "",
        }
        prompt = _build_persona_prompt(user)
        assert "없음" in prompt


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

    async def test_insight_reflected_in_prompt(
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
            state = {"user_ids": [3], "dining_data": {}}
            result = await persona_factory(state)

            prompt_3 = result["persona_prompts"]["3"]
            assert "시스템 인사이트" in prompt_3
            assert "일식을 거부함" in prompt_3
