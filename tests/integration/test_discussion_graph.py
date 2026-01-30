"""멀티에이전트 토론 그래프 통합 테스트"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from recommendation.features.iterative_discussion.workflows.graph import (
    run_iterative_discussion,
    create_discussion_graph,
)


@pytest.mark.asyncio
async def test_run_iterative_discussion_basic():
    """기본 토론 실행 테스트"""
    # Given
    user_ids = [101, 102, 103]
    candidate_restaurant_ids = ["rest_a", "rest_b", "rest_c"]
    max_rounds = 3

    # When
    result = await run_iterative_discussion(
        user_ids=user_ids,
        candidate_restaurant_ids=candidate_restaurant_ids,
        max_rounds=max_rounds,
    )

    # Then
    assert result is not None
    assert "discussion_log" in result
    assert "final_decision" in result
    assert "reasoning" in result
    assert "consensus_reached" in result
    assert "total_rounds" in result

    # 토론 로그가 있어야 함
    assert len(result["discussion_log"]) > 0

    # 최종 결정이 있어야 함
    assert result["final_decision"] is not None
    assert result["final_decision"] in candidate_restaurant_ids


@pytest.mark.asyncio
async def test_create_discussion_graph_with_mock_data():
    """Mock 데이터로 그래프 생성 및 실행 테스트"""
    # Given
    user_ids = [1, 2]
    candidate_restaurants = [
        {"id": "r1", "name": "Korean BBQ", "category": "Korean", "location": "Seoul"},
        {
            "id": "r2",
            "name": "Italian Pasta",
            "category": "Italian",
            "location": "Seoul",
        },
    ]
    max_rounds = 2

    # When
    final_state = await create_discussion_graph(
        user_ids=user_ids,
        candidate_restaurants=candidate_restaurants,
        max_rounds=max_rounds,
    )

    # Then
    assert final_state is not None
    assert "final_decision" in final_state
    assert "messages" in final_state
    assert "votes" in final_state
    assert "round" in final_state

    # 메시지가 생성되었는지 확인
    assert len(final_state["messages"]) > 0

    # 최종 결정이 후보 중 하나인지 확인
    assert final_state["final_decision"] in ["r1", "r2"]


@pytest.mark.asyncio
async def test_discussion_reaches_consensus():
    """합의 도달 시나리오 테스트 (Mock)"""
    # Given
    user_ids = [1, 2, 3]
    candidate_restaurants = [
        {
            "id": "consensus_rest",
            "name": "Best Restaurant",
            "category": "Korean",
            "location": "Seoul",
        },
    ]
    max_rounds = 1

    # When
    final_state = await create_discussion_graph(
        user_ids=user_ids,
        candidate_restaurants=candidate_restaurants,
        max_rounds=max_rounds,
    )

    # Then
    # 후보가 하나뿐이므로 합의 가능성이 높음
    assert final_state["final_decision"] == "consensus_rest"


@pytest.mark.asyncio
async def test_discussion_force_resolve():
    """최대 라운드 도달 시 강제 해결 테스트"""
    # Given
    user_ids = [1, 2, 3]
    candidate_restaurants = [
        {"id": "r1", "name": "Restaurant 1", "category": "Korean", "location": "Seoul"},
        {
            "id": "r2",
            "name": "Restaurant 2",
            "category": "Japanese",
            "location": "Seoul",
        },
        {
            "id": "r3",
            "name": "Restaurant 3",
            "category": "Chinese",
            "location": "Seoul",
        },
    ]
    max_rounds = 1  # 1라운드만 진행

    # When
    final_state = await create_discussion_graph(
        user_ids=user_ids,
        candidate_restaurants=candidate_restaurants,
        max_rounds=max_rounds,
    )

    # Then
    # 최종 결정이 있어야 함 (강제 해결 또는 합의)
    assert final_state["final_decision"] is not None
    assert final_state["final_decision"] in ["r1", "r2", "r3"]
