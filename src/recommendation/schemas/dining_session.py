from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from pydantic.alias_generators import to_camel
from typing import List, Optional, Annotated
from bson import ObjectId
from datetime import datetime

PyObjectId = Annotated[
    str, 
    BeforeValidator(lambda v: str(v) if isinstance(v, ObjectId) else v),
]

class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        # Pydantic 모델이 딕셔너리나 JSON으로 변환될 때 ObjectId 타입을 허용하도록 설정
        arbitrary_types_allowed=True 
    )

class VoteData(BaseSchema):
    likes: List[str] = Field(default=[], description="선호하는 식당 아이디 목록")
    dislikes: List[str] = Field(default=[], description="선호하지 않는 식당 아이디 목록")

class UserPersona(BaseSchema):
    user_id: str = Field(..., description="사용자 아이디")
    base_persona: str = Field(..., description="사용자의 기본 페르소나 특징")
    attributes: str = Field(..., description="해당 라운드에서 생성된 새로운 페르소나 속성")
    current_llm_votes: VoteData = Field(..., description="현재 라운드의 LLM 투표 결과")
    next_human_votes: VoteData = Field(..., description="다음 라운드를 위한 사용자의 투표(추종) 결과")

class RestaurantCandidate(BaseSchema):
    restaurant_id: str = Field(..., description="식당 아이디")
    score: float = Field(..., description="식당 추천/필터 점수")
    reasoning: str = Field(..., description="해당 식당이 추천된 사유/논리")

class DiningPhase(BaseSchema):
    round: int = Field(..., description="회식 추천 단계의 회차 (1차, 2차 등)")
    refresh_reason: str = Field(..., description="해당 페이즈가 생성된 사유 (예: 새로고침 사유)")
    user_persona: List[UserPersona] = Field(..., description="해당 라운드의 사용자별 페르소나 상태")
    served_restaurants: List[RestaurantCandidate] = Field(..., description="해당 라운드에서 사용자에게 제안된 식당들")
    created_at: str = Field(..., description="단계(Phase)가 생성된 시간")

class DiningSession(BaseSchema):
    id: Optional[PyObjectId] = Field(None, alias="_id", description="데이터베이스 고유 식별자")
    dining_id: int = Field(..., description="회식 고유 아이디")
    groups_id: int = Field(..., description="그룹 고유 아이디")
    dining_date: datetime = Field(..., description="회식 예정 날짜")
    budget: int = Field(..., description="회식 예산 범위")
    x: str = Field(..., description="회식 장소의 경도")
    y: str = Field(..., description="회식 장소의 위도")
    current_phase: int = Field(..., description="현재 진행 중인 추천 단계")
    is_completed: bool = Field(..., description="회식 장소 선정 완료 여부")
    phases: List[DiningPhase] = Field(default=[], description="전체 추천 단계(Phase) 히스토리")
    restaurant_candidate: List[RestaurantCandidate] = Field(default=[], description="현재 고려 중인 식당 후보군")
    final_restaurant: List[RestaurantCandidate] = Field(default=[], description="최종적으로 확정된 식당 정보")