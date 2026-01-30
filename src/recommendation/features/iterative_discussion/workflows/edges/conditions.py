"""LangGraph 엣지 조건 함수들"""

from typing import Dict, Any, Literal
from collections import Counter


def check_consensus(
    state: Dict[str, Any],
) -> Literal["no_consensus", "force_resolve"]:
    """합의 도달 여부를 확인하는 조건 함수

    토론 후 다음 단계를 결정합니다:
    - no_consensus: 합의 미달, 다음 라운드 진행
    - force_resolve: 최대 라운드 도달 또는 합의 도달, 최종 선정으로

    Args:
        state: 현재 상태

    Returns:
        다음 노드 이름
    """
    round_num = state.get("round", 1)
    max_rounds = state.get("max_rounds", 3)
    messages = state.get("messages", [])

    # 최대 라운드 도달 시 강제 종료
    if round_num >= max_rounds:
        return "force_resolve"

    # 토론 메시지에서 합의 신호 감지
    # TODO: LLM을 사용하여 토론 내용에서 합의 여부 판단
    # 현재는 간단한 휴리스틱 사용

    agent_messages = [
        msg
        for msg in messages
        if hasattr(msg, "name") and msg.name and msg.name.startswith("agent_")
    ]

    # 메시지가 충분하지 않으면 다음 라운드
    if len(agent_messages) < 3:
        return "no_consensus"

    # 합의 키워드 분석 (간단한 버전)
    consensus_keywords = ["동의", "찬성", "좋습니다", "괜찮", "추천"]
    disagreement_keywords = ["반대", "아니", "싫", "별로"]

    consensus_count = 0
    disagreement_count = 0

    for msg in agent_messages[-5:]:  # 최근 5개 메시지만 확인
        content = msg.content.lower()
        if any(keyword in content for keyword in consensus_keywords):
            consensus_count += 1
        if any(keyword in content for keyword in disagreement_keywords):
            disagreement_count += 1

    # 합의 비율이 70% 이상이면 종료
    total = consensus_count + disagreement_count
    if total > 0 and consensus_count / total >= 0.7:
        return "force_resolve"

    # 그 외에는 다음 라운드
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
