from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import List, Optional, TypedDict, Annotated
import operator
from datetime import datetime
from src.features.recommendation.models.enums import AllergyType, Gender, AgeGroup


# UserData Request
class UserData(BaseModel):
    """사용자 데이터 모델(사용자 특이사항은 별도의 mongoDB에서 조회)"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int = Field(
        ...,
        description="사용자 테이블의 PK (snowflake)",
        json_schema_extra={"example": 123456789},
    )
    nickname: str = Field(
        min_length=2,
        max_length=10,
        pattern=r'^[^\s!@#$%^&*(),.?":{}|<>]*$',
        description="닉네임 (2-10자, 공백 및 특수문자 금지)",
    )
    gender: Gender = Field(..., description="성별 (MALE, FEMALE)")
    age_group: AgeGroup = Field(..., description="연령대")
    allergies: List[AllergyType] = Field(..., description="알레르기 정보 목록")
    like_food_categories_id: List[str] = Field(
        ..., description="좋아하는 음식 카테고리 ID 목록"
    )
    categories_id: List[str] = Field(..., description="음식 카테고리 ID 목록")
    other_characteristics: str = Field(..., description="기타 특이사항")


class ReviewData(BaseModel):
    """리뷰 데이터 모델"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    restaurant_id: str = Field(..., description="식당 ID")
    user_id: int = Field(..., description="사용자 ID")
    rating: int = Field(..., description="평점")
    comment: str = Field(..., description="리뷰 내용")


# UserData Request
class UserDataRequest(BaseModel):
    """
    페르소나 업데이트를 위한 사용자 데이터 요청 모델입니다.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    user_data: UserData = Field(..., description="업데이트할 사용자 데이터")
    review_data: List[ReviewData] = Field(..., description="리뷰 데이터 리스트")


# UserData Response
class UserDataResponse(BaseModel):
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


# LangGraph State
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
