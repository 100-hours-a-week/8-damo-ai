from typing import TypedDict, Annotated, List
import operator
from datetime import datetime
from src.recommendation.schemas.requests.user_request import UserData


class PersonaState(TypedDict):
    """
    LangGraph에서 페르소나 업데이트 프로세스 중에 유지되는 상태 모델입니다.
    """

    # 현재 처리 중인 사용자 데이터
    user_data: UserData
    # 프로세스 중간 결과 및 상태
    is_success: bool
    status_message: Annotated[List[str], operator.add]
    process_start_time: datetime
    process_time: float
