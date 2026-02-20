"""Node 4: Consensus Assessment 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from services.iterative_discussion.app.nodes.consensus_assessment import (
    _build_moderator_feedback,
    _format_candidate_list,
    _format_dialogue_history,
    _parse_llm_json,
    consensus_assessment,
)


class TestParseLlmJson:
    def test_plain_json(self) -> None:
        text = '{"consensus_reached": true, "candidates": []}'
        result = _parse_llm_json(text)
        assert result["consensus_reached"] is True

    def test_markdown_codeblock(self) -> None:
        text = '```json\n{"consensus_reached": false, "candidates": []}\n```'
        result = _parse_llm_json(text)
        assert result["consensus_reached"] is False

    def test_codeblock_without_json_tag(self) -> None:
        text = '```\n{"consensus_reached": true, "candidates": []}\n```'
        result = _parse_llm_json(text)
        assert result["consensus_reached"] is True

    def test_invalid_json(self) -> None:
        result = _parse_llm_json("이건 JSON이 아닙니다")
        assert result == {}

    def test_empty_string(self) -> None:
        assert _parse_llm_json("") == {}


class TestFormatFunctions:
    def test_format_candidate_list(self) -> None:
        pool = [
            {"_id": "r1", "place_name": "스시히로", "category_detail": "일식"},
        ]
        result = _format_candidate_list(pool)
        assert "스시히로" in result
        assert "일식" in result

    def test_format_dialogue_history(self, sample_dialogue_history) -> None:
        result = _format_dialogue_history(sample_dialogue_history)
        assert "라운드1" in result
        assert "철수" in result


@pytest.mark.asyncio
class TestConsensusAssessment:
    async def test_consensus_reached(
        self, mock_llm_json_consensus, sample_dialogue_history
    ) -> None:
        with patch(
            "services.iterative_discussion.app.nodes.consensus_assessment.get_chat_llm",
            return_value=mock_llm_json_consensus,
        ):
            state = {
                "candidate_pool": [
                    {"_id": "r1", "place_name": "스시히로", "category_detail": "일식"},
                ],
                "dialogue_history": sample_dialogue_history,
                "round": 1,
                "max_rounds": 3,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            result = await consensus_assessment(state)

            assert result["consensus_reached"] is True
            assert len(result["consensus_candidates"]) == 5

    async def test_no_consensus_loops_back(
        self, mock_llm_no_consensus, sample_dialogue_history
    ) -> None:
        with patch(
            "services.iterative_discussion.app.nodes.consensus_assessment.get_chat_llm",
            return_value=mock_llm_no_consensus,
        ):
            state = {
                "candidate_pool": [
                    {"_id": "r1", "place_name": "스시히로", "category_detail": "일식"},
                ],
                "dialogue_history": sample_dialogue_history,
                "round": 1,
                "max_rounds": 3,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            result = await consensus_assessment(state)

            assert result["consensus_reached"] is False
            assert result["consensus_candidates"] == []

    async def test_deadlock_forces_consensus(
        self, sample_dialogue_history
    ) -> None:
        """max_rounds 도달 시 강제 합의."""
        mock_llm = MagicMock()
        # JSON 파싱 실패하는 응답
        mock_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content="파싱 불가능한 텍스트")
        )

        with patch(
            "services.iterative_discussion.app.nodes.consensus_assessment.get_chat_llm",
            return_value=mock_llm,
        ):
            candidate_pool = [
                {"_id": f"r{i}", "place_name": f"식당{i}", "category_detail": "한식"}
                for i in range(1, 8)
            ]
            state = {
                "candidate_pool": candidate_pool,
                "dialogue_history": sample_dialogue_history,
                "round": 3,
                "max_rounds": 3,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            result = await consensus_assessment(state)

            assert result["consensus_reached"] is True
            assert len(result["consensus_candidates"]) == 5
            assert result["consensus_candidates"][0]["place_name"] == "식당1"

    async def test_deadlock_with_valid_json(
        self, mock_llm_json_consensus, sample_dialogue_history
    ) -> None:
        """교착 상태에서 LLM이 유효한 JSON을 반환하면 그대로 사용."""
        with patch(
            "services.iterative_discussion.app.nodes.consensus_assessment.get_chat_llm",
            return_value=mock_llm_json_consensus,
        ):
            state = {
                "candidate_pool": [
                    {"_id": "r1", "place_name": "스시히로", "category_detail": "일식"},
                ],
                "dialogue_history": sample_dialogue_history,
                "round": 3,
                "max_rounds": 3,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            result = await consensus_assessment(state)

            assert result["consensus_reached"] is True
            assert len(result["consensus_candidates"]) == 5

    async def test_json_parse_failure_non_deadlock(
        self, sample_dialogue_history
    ) -> None:
        """교착 아닌 상태에서 JSON 파싱 실패 시 합의 미달."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content="파싱 불가")
        )

        with patch(
            "services.iterative_discussion.app.nodes.consensus_assessment.get_chat_llm",
            return_value=mock_llm,
        ):
            state = {
                "candidate_pool": [],
                "dialogue_history": sample_dialogue_history,
                "round": 1,
                "max_rounds": 3,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            result = await consensus_assessment(state)

            assert result["consensus_reached"] is False

    async def test_partial_consensus_not_reached(
        self, mock_llm_partial_consensus, sample_dialogue_history
    ) -> None:
        """3개만 반환하면 합의 미달."""
        with patch(
            "services.iterative_discussion.app.nodes.consensus_assessment.get_chat_llm",
            return_value=mock_llm_partial_consensus,
        ):
            state = {
                "candidate_pool": [
                    {"_id": f"r{i}", "place_name": f"식당{i}", "category_detail": "한식"}
                    for i in range(1, 8)
                ],
                "dialogue_history": sample_dialogue_history,
                "round": 2,
                "max_rounds": 3,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            result = await consensus_assessment(state)

            assert result["consensus_reached"] is False
            # 3개 합의 - 1개 거부(r4) = 3개 (r4는 rejected이므로 candidates에서 제거 안 됨, r4가 candidates에 없으므로 3개 유지)
            assert len(result["consensus_candidates"]) == 3

    async def test_no_backfill_in_normal_flow(
        self, mock_llm_partial_consensus, sample_dialogue_history
    ) -> None:
        """비교착 + 3개 → 보충 없이 3개 그대로."""
        with patch(
            "services.iterative_discussion.app.nodes.consensus_assessment.get_chat_llm",
            return_value=mock_llm_partial_consensus,
        ):
            state = {
                "candidate_pool": [
                    {"_id": f"r{i}", "place_name": f"식당{i}", "category_detail": "한식"}
                    for i in range(1, 8)
                ],
                "dialogue_history": sample_dialogue_history,
                "round": 2,
                "max_rounds": 3,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            result = await consensus_assessment(state)

            # 보충 없이 합의된 것만
            assert len(result["consensus_candidates"]) == 3
            reasons = [c["reason"] for c in result["consensus_candidates"]]
            assert all("보충" not in r for r in reasons)

    async def test_moderator_feedback_generated(
        self, mock_llm_partial_consensus, sample_dialogue_history
    ) -> None:
        """비교착 + 미달 → moderator_feedback 비어있지 않음."""
        with patch(
            "services.iterative_discussion.app.nodes.consensus_assessment.get_chat_llm",
            return_value=mock_llm_partial_consensus,
        ):
            state = {
                "candidate_pool": [
                    {"_id": f"r{i}", "place_name": f"식당{i}", "category_detail": "한식"}
                    for i in range(1, 8)
                ],
                "dialogue_history": sample_dialogue_history,
                "round": 2,
                "max_rounds": 3,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            result = await consensus_assessment(state)

            assert result["moderator_feedback"] != ""
            assert "사회자 정리" in result["moderator_feedback"]
            assert "추가 합의가 필요" in result["moderator_feedback"]

    async def test_moderator_feedback_empty_on_consensus(
        self, mock_llm_json_consensus, sample_dialogue_history
    ) -> None:
        """5개 합의 → moderator_feedback 빈 문자열."""
        with patch(
            "services.iterative_discussion.app.nodes.consensus_assessment.get_chat_llm",
            return_value=mock_llm_json_consensus,
        ):
            state = {
                "candidate_pool": [
                    {"_id": "r1", "place_name": "스시히로", "category_detail": "일식"},
                ],
                "dialogue_history": sample_dialogue_history,
                "round": 2,
                "max_rounds": 3,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            result = await consensus_assessment(state)

            assert result["consensus_reached"] is True
            assert result["moderator_feedback"] == ""

    async def test_deadlock_forces_backfill(
        self, mock_llm_partial_consensus, sample_dialogue_history
    ) -> None:
        """교착 시에만 보충 선정."""
        with patch(
            "services.iterative_discussion.app.nodes.consensus_assessment.get_chat_llm",
            return_value=mock_llm_partial_consensus,
        ):
            candidate_pool = [
                {"_id": f"r{i}", "place_name": f"식당{i}", "category_detail": "한식"}
                for i in range(1, 8)
            ]
            state = {
                "candidate_pool": candidate_pool,
                "dialogue_history": sample_dialogue_history,
                "round": 3,
                "max_rounds": 3,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            result = await consensus_assessment(state)

            assert result["consensus_reached"] is True
            assert len(result["consensus_candidates"]) == 5
            assert result["rejected_restaurant_ids"] == ["r4"]
