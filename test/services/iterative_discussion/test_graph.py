"""그래프 구조 + 조건부 엣지 테스트."""

import pytest

from services.iterative_discussion.app.engine.graph import (
    _after_dialogue,
    _check_error,
    _should_continue,
)


class TestCheckError:
    def test_error_returns_end(self) -> None:
        assert _check_error({"is_error": True}) == "end"

    def test_no_error_returns_continue(self) -> None:
        assert _check_error({"is_error": False}) == "continue"

    def test_missing_key_returns_continue(self) -> None:
        assert _check_error({}) == "continue"


class TestAfterDialogue:
    def test_below_min_returns_dialogue(self) -> None:
        state = {"is_error": False, "round": 1, "min_rounds": 2}
        assert _after_dialogue(state) == "dialogue"

    def test_equals_min_returns_assess(self) -> None:
        state = {"is_error": False, "round": 2, "min_rounds": 2}
        assert _after_dialogue(state) == "assess"

    def test_above_min_returns_assess(self) -> None:
        state = {"is_error": False, "round": 3, "min_rounds": 2}
        assert _after_dialogue(state) == "assess"

    def test_error_returns_end(self) -> None:
        state = {"is_error": True, "round": 1, "min_rounds": 2}
        assert _after_dialogue(state) == "end"

    def test_default_min_rounds(self) -> None:
        """min_rounds 없는 state → 기본값 2 적용."""
        state = {"is_error": False, "round": 1}
        assert _after_dialogue(state) == "dialogue"

        state_at_2 = {"is_error": False, "round": 2}
        assert _after_dialogue(state_at_2) == "assess"


class TestShouldContinue:
    def test_error_returns_end(self) -> None:
        state = {"is_error": True}
        assert _should_continue(state) == "end"

    def test_consensus_reached_returns_vote(self) -> None:
        state = {"is_error": False, "consensus_reached": True, "round": 1, "max_rounds": 3}
        assert _should_continue(state) == "vote"

    def test_max_rounds_reached_returns_vote(self) -> None:
        state = {"is_error": False, "consensus_reached": False, "round": 3, "max_rounds": 3}
        assert _should_continue(state) == "vote"

    def test_no_consensus_within_rounds_returns_dialogue(self) -> None:
        state = {"is_error": False, "consensus_reached": False, "round": 1, "max_rounds": 3}
        assert _should_continue(state) == "dialogue"

    def test_default_max_rounds(self) -> None:
        state = {"is_error": False, "consensus_reached": False, "round": 2}
        assert _should_continue(state) == "dialogue"

    def test_round_exceeds_max(self) -> None:
        state = {"is_error": False, "consensus_reached": False, "round": 5, "max_rounds": 3}
        assert _should_continue(state) == "vote"

    def test_rejected_exists_returns_preselect(self) -> None:
        """미합의 + rejected_restaurant_ids 있음 → preselect 루프백."""
        state = {
            "is_error": False,
            "consensus_reached": False,
            "round": 2,
            "max_rounds": 4,
            "rejected_restaurant_ids": ["r1"],
        }
        assert _should_continue(state) == "preselect"

    def test_no_rejected_returns_dialogue(self) -> None:
        """미합의 + rejected_restaurant_ids 비어 있음 → dialogue 루프백."""
        state = {
            "is_error": False,
            "consensus_reached": False,
            "round": 2,
            "max_rounds": 4,
            "rejected_restaurant_ids": [],
        }
        assert _should_continue(state) == "dialogue"

    def test_consensus_overrides_rejected(self) -> None:
        """합의 도달 시 rejected 있어도 vote로 진행."""
        state = {
            "is_error": False,
            "consensus_reached": True,
            "round": 2,
            "max_rounds": 4,
            "rejected_restaurant_ids": ["r1", "r2"],
        }
        assert _should_continue(state) == "vote"
