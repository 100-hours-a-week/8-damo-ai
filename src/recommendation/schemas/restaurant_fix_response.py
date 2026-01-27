from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class RestaurantFixResponse(BaseModel):
    """
    식당 정보 확정을 위한 사용자 데이터 요청 모델입니다.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    success: bool = Field(
        ..., description="API 호출 성공 여부 (true: 성공, false: 실패)"
    )
    restaurant_id: str = Field(..., description="성공적으로 처리된 식당의 고유 ID")
