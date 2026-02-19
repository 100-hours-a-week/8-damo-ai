"""Node 3: Multi-Agent Dialogue 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from services.iterative_discussion.app.nodes.multi_agent_dialogue import (
    _format_candidate_list,
    _format_previous_messages,
    multi_agent_dialogue,
)


class TestFormatCandidateList:
    def test_basic_format(self) -> None:
        pool = [
            {"place_name": "스시히로", "category_detail": "일식", "score": 0.8},
            {"place_name": "김치찌개집", "category_detail": "한식", "score": 0.6},
        ]
        result = _format_candidate_list(pool)
        assert "1. 스시히로" in result
        assert "2. 김치찌개집" in result
        assert "0.8" in result

    def test_empty_pool(self) -> None:
        assert _format_candidate_list([]) == ""


class TestFormatPreviousMessages:
    def test_with_history(self, sample_dialogue_history) -> None:
        result = _format_previous_messages(sample_dialogue_history)
        assert "[철수]" in result
        assert "[영희]" in result
        assert "스시히로" in result

    def test_empty_history(self) -> None:
        result = _format_previous_messages([])
        assert "아직 대화 없음" in result


@pytest.mark.asyncio
class TestMultiAgentDialogue:
    async def test_empty_persona_prompts(self) -> None:
        state = {
            "persona_prompts": {},
            "candidate_pool": [],
            "dialogue_history": [],
            "messages": [],
            "round": 0,
            "user_data_list": [],
        }
        result = await multi_agent_dialogue(state)
        assert result["is_error"] is True

    async def test_round_increments(
        self, mock_llm, sample_persona_prompts, sample_user_data_list
    ) -> None:
        with patch(
            "services.iterative_discussion.app.nodes.multi_agent_dialogue.get_chat_llm",
            return_value=mock_llm,
        ):
            state = {
                "persona_prompts": sample_persona_prompts,
                "candidate_pool": [
                    {"place_name": "스시히로", "category_detail": "일식", "score": 0.8},
                ],
                "dialogue_history": [],
                "messages": [],
                "round": 0,
                "user_data_list": sample_user_data_list,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            result = await multi_agent_dialogue(state)

            assert result["round"] == 1
            assert len(result["dialogue_history"]) == 3  # 3명의 페르소나
            assert len(result["messages"]) == 3

    async def test_each_persona_speaks(
        self, mock_llm, sample_persona_prompts, sample_user_data_list
    ) -> None:
        with patch(
            "services.iterative_discussion.app.nodes.multi_agent_dialogue.get_chat_llm",
            return_value=mock_llm,
        ):
            state = {
                "persona_prompts": sample_persona_prompts,
                "candidate_pool": [
                    {"place_name": "스시히로", "category_detail": "일식", "score": 0.8},
                ],
                "dialogue_history": [],
                "messages": [],
                "round": 0,
                "user_data_list": sample_user_data_list,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            result = await multi_agent_dialogue(state)

            speaker_ids = {e["user_id"] for e in result["dialogue_history"]}
            assert speaker_ids == {"1", "2", "3"}

    async def test_llm_called_per_persona(
        self, mock_llm, sample_persona_prompts, sample_user_data_list
    ) -> None:
        with patch(
            "services.iterative_discussion.app.nodes.multi_agent_dialogue.get_chat_llm",
            return_value=mock_llm,
        ):
            state = {
                "persona_prompts": sample_persona_prompts,
                "candidate_pool": [],
                "dialogue_history": [],
                "messages": [],
                "round": 0,
                "user_data_list": sample_user_data_list,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            await multi_agent_dialogue(state)
            assert mock_llm.ainvoke.call_count == 3

    async def test_previous_dialogue_passed_to_later_speakers(
        self, sample_persona_prompts, sample_user_data_list
    ) -> None:
        call_args_list = []

        async def _capture_ainvoke(messages, config=None, **kwargs):
            call_args_list.append(messages)
            return AIMessage(content="응답")

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=_capture_ainvoke)

        with patch(
            "services.iterative_discussion.app.nodes.multi_agent_dialogue.get_chat_llm",
            return_value=mock_llm,
        ):
            state = {
                "persona_prompts": sample_persona_prompts,
                "candidate_pool": [
                    {"place_name": "A", "category_detail": "한식", "score": 1.0},
                ],
                "dialogue_history": [],
                "messages": [],
                "round": 0,
                "user_data_list": sample_user_data_list,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            await multi_agent_dialogue(state)

            # 첫 번째 발언자는 FIRST_ROUND_USER_PROMPT 사용
            first_user_msg = call_args_list[0][1].content
            assert "첫 번째 발언자" in first_user_msg

            # 두 번째 이후는 DIALOGUE_USER_PROMPT 사용 (이전 대화 포함)
            second_user_msg = call_args_list[1][1].content
            assert "이전 대화" in second_user_msg
