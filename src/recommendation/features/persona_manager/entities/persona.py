from typing import List, Optional
from pydantic.alias_generators import to_camel
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from src.recommendation.enums import AllergyType, Gender, AgeGroup


class PersonaDocument(BaseModel):
    """MongoDB 'users' 컬렉션 문서 모델"""

    model_config = ConfigDict(populate_by_name=True)

    # id: int  # Snowflake ID를 _id로 쓸지, 별도 필드로 쓸지에 따라 결정
    id: int
    nickname: str
    gender: Gender
    age_group: AgeGroup
    allergies: List[AllergyType]
    like_food_categories_id: List[str]
    categories_id: List[str]
    other_characteristics: str
    base_persona: str

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
