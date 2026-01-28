from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import List
from src.recommendation.schemas.dining_data import DiningData


class RecommendationsRequest(BaseModel):
    """
    추천을 위한 사용자 데이터 요청 모델입니다.
    회식 데이터와 사용자 데이터를 함께 전달받아 처리합니다.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    dining_data: DiningData = Field(..., description="회식 데이터")
    user_ids: List[str] = Field(..., description="추천할 사용자 id 리스트")
