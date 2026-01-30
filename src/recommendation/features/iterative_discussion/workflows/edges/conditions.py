"""LangGraph 엣지 조건 함수들"""

from typing import Dict, Any, Literal
from collections import Counter


def check_consensus(
    state: Dict[str, Any],
) -> Literal["consensus", "no_consensus", "force_resolve"]:
    """합의 도달 여부를 확인하는 조건 함수

    투표 결과를 분석하여 다음 단계를 결정합니다:
    - consensus: 과반수 이상이 동의 (70% 이상)
    - no_consensus: 합의 미달, 다음 라운드 진행
    - force_resolve: 최대 라운드 도달, 강제 해결

    Args:
        state: 현재 상태

    Returns:
        다음 노드 이름
    """
    votes = state.get("votes", {})
    round_num = state.get("round", 1)
    max_rounds = state.get("max_rounds", 3)

    # 투표가 없는 경우
    if not votes:
        if round_num >= max_rounds:
            return "force_resolve"
        return "no_consensus"

    # 투표 결과 집계
    vote_counts = Counter(votes.values())
    total_votes = len(votes)

    if total_votes == 0:
        if round_num >= max_rounds:
            return "force_resolve"
        return "no_consensus"

    # 가장 많은 표를 받은 식당의 득표율
    max_votes = vote_counts.most_common(1)[0][1]
    vote_percentage = max_votes / total_votes

    # 70% 이상 득표 시 합의로 간주
    CONSENSUS_THRESHOLD = 0.7

    if vote_percentage >= CONSENSUS_THRESHOLD:
        return "consensus"

    # 최대 라운드 도달 확인
    if round_num >= max_rounds:
        return "force_resolve"

    return "no_consensus"


def should_continue_discussion(
    state: Dict[str, Any],
) -> Literal["topic_proposal", "end"]:
    """토론을 계속할지 결정하는 조건 함수

    합의에 도달하지 못한 경우 다음 라운드를 시작합니다.

    Args:
        state: 현재 상태

    Returns:
        다음 노드 이름
    """
    consensus_reached = state.get("consensus_reached", False)

    if consensus_reached:
        return "end"

    # 라운드 증가
    current_round = state.get("round", 1)
    state["round"] = current_round + 1

    return "topic_proposal"
