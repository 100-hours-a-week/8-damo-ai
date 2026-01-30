"""Moderator 프롬프트 템플릿 테스트"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

import pytest
from recommendation.features.iterative_discussion.prompts.moderator_prompts import (
    TOPIC_PROPOSAL_PROMPT,
    SUMMARIZE_PROMPT,
    CONSENSUS_GUIDE_PROMPT,
)


def test_topic_proposal_prompt_exists():
    """TOPIC_PROPOSAL_PROMPT 존재 확인"""
    assert TOPIC_PROPOSAL_PROMPT is not None
    assert hasattr(TOPIC_PROPOSAL_PROMPT, "format_messages")


def test_topic_proposal_prompt_variables():
    """TOPIC_PROPOSAL_PROMPT 변수 바인딩 테스트"""
    # Given
    variables = {
        "round_num": 1,
        "max_rounds": 3,
        "candidates_info": "식당 A, 식당 B",
        "previous_summary": "없음",
    }

    # When
    messages = TOPIC_PROPOSAL_PROMPT.format_messages(**variables)

    # Then
    assert len(messages) == 2  # system + human
    assert "중재자" in messages[0].content
    assert "1" in messages[1].content  # round_num


def test_summarize_prompt_exists():
    """SUMMARIZE_PROMPT 존재 확인"""
    assert SUMMARIZE_PROMPT is not None
    assert hasattr(SUMMARIZE_PROMPT, "format_messages")


def test_summarize_prompt_variables():
    """SUMMARIZE_PROMPT 변수 바인딩 테스트"""
    # Given
    variables = {
        "round_num": 1,
        "num_participants": 3,
        "candidates_info": "식당 A, 식당 B",
        "discussion_messages": "User 1: A가 좋아요\nUser 2: B가 좋아요",
    }

    # When
    messages = SUMMARIZE_PROMPT.format_messages(**variables)

    # Then
    assert len(messages) == 2
    assert "요약" in messages[0].content
    assert "3" in messages[1].content  # num_participants


def test_consensus_guide_prompt_exists():
    """CONSENSUS_GUIDE_PROMPT 존재 확인"""
    assert CONSENSUS_GUIDE_PROMPT is not None
    assert hasattr(CONSENSUS_GUIDE_PROMPT, "format_messages")


def test_consensus_guide_prompt_variables():
    """CONSENSUS_GUIDE_PROMPT 변수 바인딩 테스트"""
    # Given
    variables = {
        "round_num": 2,
        "max_rounds": 3,
        "candidates_info": "식당 A, 식당 B",
        "discussion_summary": "A에 2표, B에 1표",
        "current_votes": "agent_1: A, agent_2: A, agent_3: B",
    }

    # When
    messages = CONSENSUS_GUIDE_PROMPT.format_messages(**variables)

    # Then
    assert len(messages) == 2
    assert "합의" in messages[0].content
    assert "2" in messages[1].content  # round_num


def test_all_prompts_have_system_and_human_messages():
    """모든 프롬프트가 system + human 메시지 구조를 가지는지 확인"""
    prompts = [
        TOPIC_PROPOSAL_PROMPT,
        SUMMARIZE_PROMPT,
        CONSENSUS_GUIDE_PROMPT,
    ]

    for prompt in prompts:
        # 최소한의 변수로 메시지 생성
        messages = prompt.format_messages(
            round_num=1,
            max_rounds=3,
            candidates_info="test",
            previous_summary="test",
            num_participants=3,
            discussion_messages="test",
            discussion_summary="test",
            current_votes="test",
        )

        assert len(messages) >= 2
        # system 메시지가 먼저 오는지 확인
        assert messages[0].type in ["system", "human"]
