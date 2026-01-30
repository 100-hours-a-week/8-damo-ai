"""에이전트 토론 노드"""

from typing import Dict, Any, List
from langchain_core.messages import AIMessage

from ...agents import PersonaAgent


async def agent_discussion_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """에이전트들이 순차적으로 의견을 제시하는 노드

    Round-Robin 방식으로 각 PersonaAgent가 발언합니다.

    Args:
        state: 현재 상태

    Returns:
        에이전트 발언이 추가된 상태 업데이트
    """
    user_ids = state.get("user_ids", [])
    candidates = state.get("candidates", [])
    messages = state.get("messages", [])
    round_num = state.get("round", 1)
    max_rounds = state.get("max_rounds", 3)

    new_messages: List[AIMessage] = []

    # 토론 주제 설정
    topic = f"라운드 {round_num}: 후보 식당 논의"

    # 각 에이전트가 순차적으로 발언
    for user_id in user_ids:
        # PersonaAgent 생성
        # TODO: 실제 구현에서는 페르소나 데이터를 DB에서 조회
        persona_agent = PersonaAgent(
            user_id=user_id,
            persona_data=_get_mock_persona(user_id),
        )

        # 토론 참여
        agent_message = await persona_agent.participate_discussion(
            round_num=round_num,
            candidates=candidates,
            topic=topic,
            previous_messages=messages + new_messages,  # 누적된 메시지 포함
            max_rounds=max_rounds,
        )

        new_messages.append(agent_message)

    return {"messages": new_messages}


def _get_mock_persona(user_id: int) -> Dict[str, Any]:
    """Mock 페르소나 데이터 생성

    실제 구현에서는 DB에서 조회하거나 API로 가져옴

    Args:
        user_id: 사용자 ID

    Returns:
        페르소나 데이터
    """
    # 다양한 페르소나 시뮬레이션
    personas = {
        101: {
            "name": "김철수",
            "preferences": {
                "likes": ["한식", "고기", "매운 음식"],
                "dislikes": ["생선회", "달콤한 음식"],
            },
            "constraints": ["주차 가능한 곳"],
            "personality": "직설적이고 솔직함",
        },
        102: {
            "name": "이영희",
            "preferences": {
                "likes": ["이탈리안", "파스타", "와인"],
                "dislikes": ["너무 매운 음식"],
            },
            "constraints": ["조용한 분위기"],
            "personality": "세련되고 신중함",
        },
        103: {
            "name": "박민수",
            "preferences": {
                "likes": ["일식", "초밥", "라멘"],
                "dislikes": ["기름진 음식"],
            },
            "constraints": ["가격대 합리적"],
            "personality": "분석적이고 논리적",
        },
    }

    # 기본 페르소나
    default_persona = {
        "name": f"User {user_id}",
        "preferences": {
            "likes": ["한식"],
            "dislikes": [],
        },
        "constraints": [],
        "personality": "친근함",
    }

    return personas.get(user_id, default_persona)
