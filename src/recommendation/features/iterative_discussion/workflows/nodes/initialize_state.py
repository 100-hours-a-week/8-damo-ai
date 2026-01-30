"""상태 초기화 노드"""

from typing import Dict, Any
from langchain_core.messages import SystemMessage


async def initialize_state_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """토론 시작 시 상태를 초기화하는 노드

    Args:
        state: 현재 상태

    Returns:
        초기화된 상태 업데이트
    """
    # 시스템 메시지 추가
    system_message = SystemMessage(
        content=f"""
        멀티에이전트 토론을 시작합니다.
        참여자: {len(state.get("user_ids", []))}명
        후보 식당: {len(state.get("candidates", []))}개
        최대 라운드: {state.get("max_rounds", 3)}
        
        각 에이전트는 자신의 페르소나를 기반으로 의견을 제시하고,
        다른 에이전트의 의견을 듣고 타협점을 찾아야 합니다.
        """
    )

    return {
        "round": 1,
        "messages": [system_message],
        "votes": {},
        "consensus_reached": False,
        "final_decision": None,
    }
