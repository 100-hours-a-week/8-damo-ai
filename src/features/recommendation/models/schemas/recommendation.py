from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import List, Optional, TypedDict, Annotated
import operator
from datetime import datetime
from .user import UserData


# DiningData
class DiningData(BaseModel):
    """회식 데이터 모델"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    dining_id: int = Field(
        ...,
        description="회식 테이블의 PK (snowflake)",
        json_schema_extra={"example": 1234567890},
    )
    groups_id: int = Field(..., description="그룹 테이블의 PK")
    dining_date: datetime = Field(..., description="회식 진행 날짜")
    budget: int = Field(..., description="회식 진행 예산")


# RecommendedItem
class RecommendedItem(BaseModel):
    """추천 식당 아이템"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    restaurant_id: str = Field(..., description="식당 식별자")
    reasoning_description: str = Field(..., max_length=500, description="추천 사유")


# Recommendation Request
class RecommendationRequest(BaseModel):
    """
    추천을 위한 사용자 데이터 요청 모델입니다.
    회식 데이터와 사용자 데이터를 함께 전달받아 처리합니다.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    dining_data: DiningData = Field(..., description="회식 데이터")
    user_ids: List[int] = Field(..., description="추천할 사용자 id 리스트")


# Recommendation Response
class RecommendationResponse(BaseModel):
    """
    추천 결과 응답 모델입니다.
    처리 결과 상태와 소요 시간, 추천 식당 정보 상위 5개를 포함합니다.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    recommendation_count: int = Field(..., description="추천된 횟수")
    recommended_items: List[RecommendedItem] = Field(
        ..., description="추천 식당 정보 상위 5개"
    )


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


# Analyze Refresh Request
class AnalyzeRefreshRequest(RecommendationRequest):
    """
    재추천을 위한 사용자 데이터 요청 모델입니다.
    회식 데이터와 사용자 데이터를 함께 전달받아 처리합니다.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    # dining_id는 dining_data 내부에 포함되어 있으므로 제거
    vote_result_list: List[RestaurantVoteResult] = Field(
        ..., description="식당 투표 결과 리스트"
    )


# LangGraph State
class RecommendationState(TypedDict):
    """
    LangGraph에서 식당 추천 프로세스 중에 유지되는 상태 모델입니다.
    """

    # 현재 처리 중인 사용자 데이터
    user_data: List[UserData]
    dining_data: DiningData
    is_refresh: bool
    refresh_count: int
    # 프로세스 중간 결과 및 상태
    is_success: bool
    status_message: Annotated[List[str], operator.add]
    process_start_time: datetime
    process_time: float
