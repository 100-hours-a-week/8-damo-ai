from datetime import datetime
from enum import Enum
from typing import Optional, Literal, Annotated
from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from pydantic.alias_generators import to_camel
from bson import ObjectId

class EventType(str, Enum):
    RECOMMENDATION_REQUEST = "RECOMMENDATION_REQUEST"
    RECOMMENDATION_STREAMING = "RECOMMENDATION_STREAMING"
    RECOMMENDATION_RESPONSE = "RECOMMENDATION_RESPONSE"
    RECOMMENDATION_RETRY = "RECOMMENDATION_RETRY"
    PERSONA_REQUEST = "PERSONA_REQUEST"
    OCR_REQUEST = "OCR_REQUEST"
    OCR_RESPONSE = "OCR_RESPONSE"
    FIX_REQUEST = "FIX_REQUEST"

class TopicType(str, Enum):
    RECOMMENDATION_REQUEST = "recommendation-request"
    RECOMMENDATION_STREAMING = "recommendation-streaming"
    RECOMMENDATION_RESPONSE = "recommendation-response"
    RECOMMENDATION_RETRY = "recommendation-retry"
    PERSONA_REQUEST = "user-persona-update"
    OCR_REQUEST = "ocr-request"
    OCR_RESPONSE = "ocr-response"
    FIX_REQUEST = "fix-request"

PyObjectId = Annotated[
    str, 
    BeforeValidator(lambda v: str(v) if isinstance(v, ObjectId) else v),
]

class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        arbitrary_types_allowed=True 
    )

# 추천 요청 페이로드
class DiningData(BaseSchema):
    dining_id: int = Field(..., description="회식 고유 아이디")
    groups_id: int = Field(..., description="그룹 고유 아이디")
    dining_date: datetime = Field(..., description="회식 예정 날짜")
    budget: int = Field(..., description="회식 예산 범위")
    x: str = Field(..., description="회식 장소의 경도")
    y: str = Field(..., description="회식 장소의 위도")

class RecommendationRequestData(BaseSchema):
    dining_data: DiningData
    user_ids: list[int]

class RecommendationRequestPayload(BaseSchema):
    event_id: int
    event_type: EventType
    payload: RecommendationRequestData

# 추천 응답 페이로드
class RecommendedItem(BaseSchema):
    restaurant_id: str
    reasoning_description: Optional[str] = None

class RecommendationResponseData(BaseSchema):
    group_id: int
    recommendation_count: int
    recommended_items: list[RecommendedItem]

class RecommendationResponsePayload(BaseSchema):
    event_id: int
    event_type: EventType
    payload: RecommendationResponseData

# 사용자 응답 페이로드
class PersonaRequestData(BaseSchema):
    user_id: int
    nickname: str
    gender: str
    age_group: str
    allergies: list[str]
    like_foods: list[str]
    like_ingredients: list[str]
    other_characteristics: Optional[str] = None

class PersonaRequestPayload(BaseSchema):
    event_id: int
    event_type: EventType
    payload: PersonaRequestData

