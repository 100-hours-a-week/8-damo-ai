"""Node 5: Persona Voting 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from services.iterative_discussion.app.nodes.persona_voting import (
    _parse_llm_json,
    _tally_votes,
    persona_voting,
)


class TestTallyVotes:
    def test_basic_tally(self) -> None:
        all_votes = [
            {
                "user_id": "1",
                "votes": [
                    {"restaurant_id": "r1", "approve": True},
                    {"restaurant_id": "r2", "approve": False},
                ],
            },
            {
                "user_id": "2",
                "votes": [
                    {"restaurant_id": "r1", "approve": True},
                    {"restaurant_id": "r2", "approve": True},
                ],
            },
        ]
        candidates = [
            {"restaurant_id": "r1", "place_name": "A", "reason": ""},
            {"restaurant_id": "r2", "place_name": "B", "reason": ""},
        ]
        pool = [
            {"_id": "r1", "score": 0.8},
            {"_id": "r2", "score": 0.6},
        ]

        result = _tally_votes(all_votes, candidates, pool)

        assert result[0]["restaurant_id"] == "r1"
        assert result[0]["approve_count"] == 2
        assert result[1]["restaurant_id"] == "r2"
        assert result[1]["approve_count"] == 1

    def test_tiebreak_by_initial_score(self) -> None:
        all_votes = [
            {
                "user_id": "1",
                "votes": [
                    {"restaurant_id": "r1", "approve": True},
                    {"restaurant_id": "r2", "approve": True},
                ],
            },
        ]
        candidates = [
            {"restaurant_id": "r1", "place_name": "A", "reason": ""},
            {"restaurant_id": "r2", "place_name": "B", "reason": ""},
        ]
        pool = [
            {"_id": "r1", "score": 0.5},
            {"_id": "r2", "score": 0.9},
        ]

        result = _tally_votes(all_votes, candidates, pool)

        # 찬성수 동일(1) → 초기 점수로 정렬
        assert result[0]["restaurant_id"] == "r2"
        assert result[0]["initial_score"] == 0.9

    def test_no_votes(self) -> None:
        result = _tally_votes([], [], [])
        assert result == []

    def test_all_rejected(self) -> None:
        all_votes = [
            {
                "user_id": "1",
                "votes": [
                    {"restaurant_id": "r1", "approve": False},
                ],
            },
        ]
        candidates = [{"restaurant_id": "r1", "place_name": "A", "reason": ""}]
        pool = [{"_id": "r1", "score": 0.5}]

        result = _tally_votes(all_votes, candidates, pool)
        assert result[0]["approve_count"] == 0


@pytest.mark.asyncio
class TestPersonaVoting:
    async def test_empty_consensus_candidates(self) -> None:
        state = {
            "persona_prompts": {"1": "prompt"},
            "consensus_candidates": [],
            "dialogue_history": [],
            "candidate_pool": [],
            "user_data_list": [],
        }
        result = await persona_voting(state)
        assert result["is_error"] is True

    async def test_successful_voting(
        self,
        mock_llm_json_voting,
        sample_persona_prompts,
        sample_user_data_list,
        sample_consensus_candidates,
        sample_dialogue_history,
    ) -> None:
        with patch(
            "services.iterative_discussion.app.nodes.persona_voting.get_chat_llm",
            return_value=mock_llm_json_voting,
        ):
            state = {
                "persona_prompts": sample_persona_prompts,
                "consensus_candidates": sample_consensus_candidates,
                "dialogue_history": sample_dialogue_history,
                "candidate_pool": [
                    {"_id": "r1", "score": 0.8},
                    {"_id": "r2", "score": 0.7},
                    {"_id": "r3", "score": 0.5},
                    {"_id": "r6", "score": 0.6},
                    {"_id": "r5", "score": 0.65},
                ],
                "user_data_list": sample_user_data_list,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            result = await persona_voting(state)

            assert "is_error" not in result
            assert len(result["persona_votes"]) == 3  # 3명 투표
            assert len(result["final_selection"]) == 5
            assert "최종 1위" in result["final_decision"]

    async def test_vote_parse_failure_fallback(
        self,
        sample_persona_prompts,
        sample_user_data_list,
        sample_consensus_candidates,
    ) -> None:
        """JSON 파싱 실패 시 전부 찬성 처리."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content="파싱 불가능한 텍스트")
        )

        with patch(
            "services.iterative_discussion.app.nodes.persona_voting.get_chat_llm",
            return_value=mock_llm,
        ):
            state = {
                "persona_prompts": sample_persona_prompts,
                "consensus_candidates": sample_consensus_candidates,
                "dialogue_history": [],
                "candidate_pool": [{"_id": "r1", "score": 0.5}],
                "user_data_list": sample_user_data_list,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            result = await persona_voting(state)

            # 3명 모두 fallback → 모든 후보에 찬성
            for vote_entry in result["persona_votes"]:
                for v in vote_entry["votes"]:
                    assert v["approve"] is True
                    assert "파싱 실패" in v["reasoning"]

    async def test_final_selection_sorted(
        self,
        mock_llm_json_voting,
        sample_persona_prompts,
        sample_user_data_list,
        sample_consensus_candidates,
    ) -> None:
        with patch(
            "services.iterative_discussion.app.nodes.persona_voting.get_chat_llm",
            return_value=mock_llm_json_voting,
        ):
            state = {
                "persona_prompts": sample_persona_prompts,
                "consensus_candidates": sample_consensus_candidates,
                "dialogue_history": [],
                "candidate_pool": [
                    {"_id": "r1", "score": 0.8},
                    {"_id": "r2", "score": 0.7},
                    {"_id": "r3", "score": 0.5},
                    {"_id": "r6", "score": 0.6},
                    {"_id": "r5", "score": 0.65},
                ],
                "user_data_list": sample_user_data_list,
                "dining_data": {"diningId": 100},
                "langfuse_trace_id": "",
            }
            result = await persona_voting(state)

            selection = result["final_selection"]
            approve_counts = [s["approve_count"] for s in selection]
            assert approve_counts == sorted(approve_counts, reverse=True)
