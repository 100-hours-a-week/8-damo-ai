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
            assert "첫 번째로 말합니다" in first_user_msg

            # 두 번째 이후는 DIALOGUE_USER_PROMPT 사용 (이전 대화 포함)
            second_user_msg = call_args_list[1][1].content
            assert "이전 대화" in second_user_msg

    async def test_moderator_feedback_injected(
        self, mock_llm, sample_persona_prompts, sample_user_data_list
    ) -> None:
        """moderator_feedback이 있으면 dialogue_history에 사회자 엔트리 추가."""
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
                "round": 1,
                "user_data_list": sample_user_data_list,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
                "moderator_feedback": "[사회자 정리]\n- 2개 추가 합의 필요",
            }
            result = await multi_agent_dialogue(state)

            moderator_entries = [
                e for e in result["dialogue_history"]
                if e["user_id"] == "moderator"
            ]
            assert len(moderator_entries) == 1
            assert "사회자 정리" in moderator_entries[0]["content"]

    async def test_moderator_feedback_cleared(
        self, mock_llm, sample_persona_prompts, sample_user_data_list
    ) -> None:
        """반환 dict의 moderator_feedback은 빈 문자열."""
        with patch(
            "services.iterative_discussion.app.nodes.multi_agent_dialogue.get_chat_llm",
            return_value=mock_llm,
        ):
            state = {
                "persona_prompts": sample_persona_prompts,
                "candidate_pool": [],
                "dialogue_history": [],
                "messages": [],
                "round": 1,
                "user_data_list": sample_user_data_list,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
                "moderator_feedback": "사회자 피드백",
            }
            result = await multi_agent_dialogue(state)

            assert result["moderator_feedback"] == ""

    async def test_guided_prompt_used(
        self, sample_persona_prompts, sample_user_data_list
    ) -> None:
        """moderator_feedback이 있으면 GUIDED_ROUND_USER_PROMPT 사용."""
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
                "dialogue_history": [
                    {"user_id": "1", "nickname": "철수", "round": 1, "content": "이전 발언"},
                ],
                "messages": [],
                "round": 1,
                "user_data_list": sample_user_data_list,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
                "moderator_feedback": "[사회자 정리]\n- 테스트 피드백",
            }
            await multi_agent_dialogue(state)

            # 모든 페르소나가 GUIDED_ROUND_USER_PROMPT을 사용
            for call_args in call_args_list:
                user_msg = call_args[1].content
                assert "사회자 안내" in user_msg
