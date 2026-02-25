from datetime import datetime
from enum import Enum
from typing import Optional, Literal, Annotated
from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from pydantic.alias_generators import to_camel
from bson import ObjectId

class EventType(str, Enum):
    RECOMMENDATION_REQUEST = "RECOMMENDATION_REQUEST"
    RECOMMENDATION_RESPONSE = "RECOMMENDATION_RESPONSE"
    RECOMMENDATION_REFRESH_REQUEST = "RECOMMENDATION_REFRESH_REQUEST"
    RECOMMENDATION_STREAMING = "RECOMMENDATION_STREAMING"
    RESTAURANT_CONFIRMED = "RESTAURANT_CONFIRMED"
    USER_PERSONA_UPDATE = "USER_PERSONA_UPDATE"
    RECEIPT_OCR_REQUEST = "RECEIPT_OCR_REQUEST"
    RECEIPT_OCR_RESPONSE = "RECEIPT_OCR_RESPONSE"

class TopicType(str, Enum):
    RECOMMENDATION_REQUEST = "recommendation-request"
    RECOMMENDATION_RESPONSE = "recommendation-response"
    RECOMMENDATION_REFRESH_REQUEST = "recommendation-refresh-request"
    RECOMMENDATION_STREAMING = "recommendation-streaming"
    RESTAURANT_CONFIRMED = "restaurant-confirmed"
    USER_PERSONA_UPDATE = "user-persona-update"
    RECEIPT_OCR_REQUEST = "receipt-ocr-request"
    RECEIPT_OCR_RESPONSE = "receipt-ocr-response"
    

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
class UserPersonaUpdateData(BaseSchema):
    user_id: int
    nickname: str
    gender: str
    age_group: str
    allergies: list[str]
    like_foods: list[str]
    like_ingredients: list[str]
    other_characteristics: Optional[str] = None

class UserPersonaUpdatePayload(BaseSchema):
    event_id: int
    event_type: EventType
    payload: UserPersonaUpdateData

# 장소 재추천 페이로드
class VoteResultData(BaseSchema):
    restaurant_id: str
    like_count: int
    dislike_count: int
    liked_user_ids: list[int]
    disliked_user_ids: list[int]

class RecommendationRefreshRequestData(BaseSchema):
    dining_data: DiningData
    user_ids: list[int]
    vote_result_list: list[VoteResultData]

class RecommendationRefreshRequestPayload(BaseSchema):
    event_id: int
    event_type: EventType
    payload: RecommendationRefreshRequestData

