from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class ReviewData(BaseModel):
    """리뷰 데이터 모델"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    restaurant_id: str = Field(..., description="식당 ID")
    user_id: int = Field(..., description="사용자 ID")
    rating: int = Field(..., description="평점")
    comment: str = Field(..., description="리뷰 내용")
