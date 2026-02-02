from typing import List, Optional
from pydantic.alias_generators import to_camel
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from src.recommendation.enums import AllergyType, Gender, AgeGroup
from src.recommendation.schemas.review_data import ReviewData


class Users(BaseModel):
    """MongoDB 'users' 컬렉션 문서 모델"""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    id: int
    nickname: str
    gender: Gender
    age_group: AgeGroup
    allergies: List[AllergyType] = Field(default_factory=list)
    like_foods: List[str] = Field(default_factory=list)
    like_ingredients: List[str] = Field(default_factory=list)
    other_characteristics: str = ""
    reviews: List[ReviewData] = Field(default_factory=list)
    base_persona: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
