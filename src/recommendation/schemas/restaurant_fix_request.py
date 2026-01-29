from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import List
from src.recommendation.schemas.restaurant_vote_result import RestaurantVoteResult
from src.recommendation.schemas.dining_data import DiningData


class RestaurantFixRequest(BaseModel):
    """
    식당 정보 확정을 위한 사용자 데이터 요청 모델입니다.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    dining_data: DiningData = Field(..., description="회식 데이터")
    restaurant_id: str = Field(..., description="식당 식별자")
    vote_result_list: List[RestaurantVoteResult] = Field(
        ..., description="식당 투표 결과 리스트"
    )
