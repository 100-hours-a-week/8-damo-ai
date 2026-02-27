"""Self Evolution 노드 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from services.iterative_discussion.app.nodes.self_evolution import (
    _fetch_previous_votes,
    _find_mismatches,
    self_evolution,
)


class TestFindMismatches:
    def test_no_mismatch(self) -> None:
        previous_votes = [
            {
                "user_id": "1",
                "votes": [
                    {"restaurant_id": "r1", "approve": True, "reasoning": "좋아요"},
                ],
            },
        ]
        vote_result_list = [
            {"restaurant_id": "r1", "liked_user_ids": [1], "disliked_user_ids": []},
        ]
        result = _find_mismatches(previous_votes, vote_result_list)
        assert result == []

    def test_mismatch_predicted_approve_actual_dislike(self) -> None:
        previous_votes = [
            {
                "user_id": "1",
                "votes": [
                    {"restaurant_id": "r1", "approve": True, "reasoning": "좋을 것 같아요"},
                ],
            },
        ]
        vote_result_list = [
            {"restaurant_id": "r1", "liked_user_ids": [], "disliked_user_ids": [1]},
        ]
        result = _find_mismatches(previous_votes, vote_result_list)
        assert len(result) == 1
        assert result[0]["predicted"] is True
        assert result[0]["actual"] == "dislike"

    def test_mismatch_predicted_reject_actual_like(self) -> None:
        previous_votes = [
            {
                "user_id": "2",
                "votes": [
                    {"restaurant_id": "r2", "approve": False, "reasoning": "별로"},
                ],
            },
        ]
        vote_result_list = [
            {"restaurant_id": "r2", "liked_user_ids": [2], "disliked_user_ids": []},
        ]
        result = _find_mismatches(previous_votes, vote_result_list)
        assert len(result) == 1
        assert result[0]["predicted"] is False
        assert result[0]["actual"] == "like"

    def test_user_did_not_vote(self) -> None:
        """유저가 실제 투표를 안 한 식당은 스킵."""
        previous_votes = [
            {
                "user_id": "1",
                "votes": [
                    {"restaurant_id": "r1", "approve": True, "reasoning": ""},
                ],
            },
        ]
        vote_result_list = [
            {"restaurant_id": "r1", "liked_user_ids": [], "disliked_user_ids": []},
        ]
        result = _find_mismatches(previous_votes, vote_result_list)
        assert result == []

    def test_camelCase_keys(self) -> None:
        """camelCase 키도 처리."""
        previous_votes = [
            {
                "user_id": "1",
                "votes": [
                    {"restaurant_id": "r1", "approve": True, "reasoning": ""},
                ],
            },
        ]
        vote_result_list = [
            {"restaurantId": "r1", "likedUserIds": [], "dislikedUserIds": [1]},
        ]
        result = _find_mismatches(previous_votes, vote_result_list)
        assert len(result) == 1

    def test_multiple_users_multiple_restaurants(self) -> None:
        previous_votes = [
            {
                "user_id": "1",
                "votes": [
                    {"restaurant_id": "r1", "approve": True, "reasoning": ""},
                    {"restaurant_id": "r2", "approve": False, "reasoning": ""},
                ],
            },
            {
                "user_id": "2",
                "votes": [
                    {"restaurant_id": "r1", "approve": False, "reasoning": ""},
                ],
            },
        ]
        vote_result_list = [
            {"restaurant_id": "r1", "liked_user_ids": [2], "disliked_user_ids": [1]},
            {"restaurant_id": "r2", "liked_user_ids": [1], "disliked_user_ids": []},
        ]
        result = _find_mismatches(previous_votes, vote_result_list)
        # user1: r1 예측찬성 실제반대, r2 예측반대 실제찬성 → 2개
        # user2: r1 예측반대 실제찬성 → 1개
        assert len(result) == 3


@pytest.mark.asyncio
class TestSelfEvolution:
    async def test_no_dining_id(self, sample_persona_prompts) -> None:
        state = {
            "vote_result_list": [{"restaurant_id": "r1"}],
            "dining_data": {},
            "persona_prompts": sample_persona_prompts,
            "langfuse_trace_id": "",
        }
        result = await self_evolution(state)
        assert result == {}

    async def test_no_previous_votes(self, sample_persona_prompts) -> None:
        mock_db = MagicMock()
        mock_db.read_one = AsyncMock(return_value=None)

        with patch(
            "services.iterative_discussion.app.nodes.self_evolution.DBManager",
            return_value=mock_db,
        ):
            state = {
                "vote_result_list": [{"restaurant_id": "r1"}],
                "dining_data": {"diningId": 100},
                "persona_prompts": sample_persona_prompts,
                "langfuse_trace_id": "",
            }
            result = await self_evolution(state)
            assert result == {}

    async def test_all_predictions_correct(self, sample_persona_prompts) -> None:
        """전부 일치하면 보정 불필요."""
        session_doc = {
            "phases": [
                {
                    "persona_votes": [
                        {
                            "user_id": "1",
                            "votes": [
                                {"restaurant_id": "r1", "approve": True, "reasoning": ""},
                            ],
                        },
                    ],
                },
            ],
        }

        mock_sessions_db = MagicMock()
        mock_sessions_db.read_one = AsyncMock(return_value=session_doc)

        mock_users_db = MagicMock()

        call_count = {"n": 0}

        def _make_db(col_name=None, **kwargs):
            call_count["n"] += 1
            if col_name == "dining_sessions":
                return mock_sessions_db
            return mock_users_db

        with patch(
            "services.iterative_discussion.app.nodes.self_evolution.DBManager",
            side_effect=_make_db,
        ):
            state = {
                "vote_result_list": [
                    {"restaurant_id": "r1", "liked_user_ids": [1], "disliked_user_ids": []},
                ],
                "dining_data": {"diningId": 100},
                "persona_prompts": sample_persona_prompts,
                "langfuse_trace_id": "",
            }
            result = await self_evolution(state)
            assert result == {}

    async def test_mismatch_generates_insight(self, sample_persona_prompts) -> None:
        """불일치 시 LLM으로 인사이트 생성 + persona_prompts 업데이트."""
        session_doc = {
            "phases": [
                {
                    "persona_votes": [
                        {
                            "user_id": "1",
                            "votes": [
                                {"restaurant_id": "r1", "approve": True, "reasoning": "초밥 좋아요"},
                            ],
                        },
                    ],
                },
            ],
        }

        mock_sessions_db = MagicMock()
        mock_sessions_db.read_one = AsyncMock(return_value=session_doc)

        mock_users_db = MagicMock()
        mock_users_db.read_one = AsyncMock(return_value={"id": 1, "otherCharacteristics": ""})
        mock_users_db.update_one = AsyncMock()

        def _make_db(col_name=None, **kwargs):
            if col_name == "dining_sessions":
                return mock_sessions_db
            return mock_users_db

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content="실제로는 초밥을 싫어하는 경향이 있음")
        )

        with patch(
            "services.iterative_discussion.app.nodes.self_evolution.DBManager",
            side_effect=_make_db,
        ), patch(
            "services.iterative_discussion.app.nodes.self_evolution.get_chat_llm",
            return_value=mock_llm,
        ):
            state = {
                "vote_result_list": [
                    {"restaurant_id": "r1", "liked_user_ids": [], "disliked_user_ids": [1]},
                ],
                "dining_data": {"diningId": 100},
                "persona_prompts": dict(sample_persona_prompts),
                "langfuse_trace_id": "",
            }
            result = await self_evolution(state)

            assert "persona_prompts" in result
            assert "[System Insight]" in result["persona_prompts"]["1"]
            assert "초밥을 싫어하는" in result["persona_prompts"]["1"]

            # DB에도 저장되었는지 확인
            mock_users_db.update_one.assert_called_once()
