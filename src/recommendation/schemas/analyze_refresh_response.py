from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import List
from src.recommendation.schemas.recommended_item import RecommendedItem


class AnalyzeRefreshResponse(BaseModel):
    """
    재추천 결과 응답 모델입니다.
    처리 결과 상태와 소요 시간, 추천 식당 정보 상위 5개를 포함합니다.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    recommendation_count: int = Field(..., description="추천된 횟수")
    recommended_items: List[RecommendedItem] = Field(
        ..., description="추천 식당 정보 상위 5개"
    )
