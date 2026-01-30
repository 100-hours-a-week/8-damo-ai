from typing import List, Dict, Optional, TypedDict, Any
from langchain_core.messages import BaseMessage


class DiscussionState(TypedDict):
    """멀티에이전트 토론 시스템의 상태를 관리하는 TypedDict

    Attributes:
        round: 현재 라운드 번호
        messages: 전체 대화 로그
        candidates: 후보 식당 목록 (Restaurant 객체들)
        votes: agent_id -> restaurant_id 투표 현황
        consensus_reached: 합의 도달 여부
        final_decision: 최종 선정된 식당 ID
        user_ids: 참여 사용자 ID 목록
        max_rounds: 최대 라운드 수
    """

    round: int
    messages: List[BaseMessage]
    candidates: List[Any]  # List[Restaurant] - 순환 참조 방지를 위해 Any 사용
    votes: Dict[str, str]
    consensus_reached: bool
    final_decision: Optional[str]
    user_ids: List[int]
    max_rounds: int
