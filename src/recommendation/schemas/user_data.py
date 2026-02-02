from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import List
from src.recommendation.enums import AllergyType, Gender, AgeGroup


class UserData(BaseModel):
    """사용자 데이터 모델 (API 통신용)"""

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
    like_foods: List[str] = Field(..., description="좋아하는 음식 카테고리 ID 목록")
    like_ingredients: List[str] = Field(
        ..., description="좋아하는 재료 카테고리 ID 목록"
    )
    other_characteristics: str = Field(..., description="기타 특이사항")
