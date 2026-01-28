from typing import TypedDict, Optional
from src.recommendation.schemas.update_persona_db_request import UpdatePersonaDBRequest
from src.recommendation.features.persona_manager.entities.persona import PersonaDocument


class PersonaState(TypedDict):
    """
    페르소나 생성/업데이트 워크플로우의 상태(State) 정의
    """

    # 입력 데이터
    request_data: UpdatePersonaDBRequest

    # 중간 생성 데이터
    generated_base_persona: Optional[str]  # LLM이 생성한 페르소나 텍스트

    # 최종 결과
    final_document: Optional[PersonaDocument]
