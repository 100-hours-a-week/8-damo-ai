from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import List


class RestaurantVoteResult(BaseModel):
    """식당 투표 결과 모델"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    restaurant_id: str = Field(..., description="식당 식별자")
    like_count: int = Field(..., description="좋아요 횟수")
    dislike_count: int = Field(..., description="싫어요 횟수")
    liked_user_ids: List[int] = Field(..., description="좋아요를 누른 사용자 id 리스트")
    disliked_user_ids: List[int] = Field(
        ..., description="싫어요를 누른 사용자 id 리스트"
    )
