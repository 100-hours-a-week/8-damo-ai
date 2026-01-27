from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class UpdatePersonaDBResponse(BaseModel):
    """
    페르소나 업데이트 결과 응답 모델입니다.
    처리 결과 상태와 소요 시간, 대상 사용자 ID를 포함합니다.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    success: bool = Field(
        ..., description="API 호출 성공 여부 (true: 성공, false: 실패)"
    )
    user_id: int = Field(
        ..., description="성공적으로 처리된 사용자의 고유 ID (Snowflake ID)"
    )
