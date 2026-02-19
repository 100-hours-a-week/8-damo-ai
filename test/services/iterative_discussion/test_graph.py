"""그래프 구조 + 조건부 엣지 테스트."""

import pytest

from services.iterative_discussion.app.engine.graph import (
    _after_persona_factory,
    _check_error,
    _should_continue,
)


class TestAfterPersonaFactory:
    def test_error_returns_end(self) -> None:
        state = {"is_error": True}
        assert _after_persona_factory(state) == "end"

    def test_with_vote_result_returns_evolve(self) -> None:
        state = {"is_error": False, "vote_result_list": [{"restaurant_id": "r1"}]}
        assert _after_persona_factory(state) == "evolve"

    def test_no_vote_result_returns_preselect(self) -> None:
        state = {"is_error": False, "vote_result_list": []}
        assert _after_persona_factory(state) == "preselect"

    def test_missing_vote_result_returns_preselect(self) -> None:
        state = {"is_error": False}
        assert _after_persona_factory(state) == "preselect"


class TestCheckError:
    def test_error_returns_end(self) -> None:
        assert _check_error({"is_error": True}) == "end"

    def test_no_error_returns_continue(self) -> None:
        assert _check_error({"is_error": False}) == "continue"

    def test_missing_key_returns_continue(self) -> None:
        assert _check_error({}) == "continue"


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
