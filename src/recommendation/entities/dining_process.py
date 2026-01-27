from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from datetime import datetime


class LLMVotes(BaseModel):
    """LLM 투표 결과"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    likes: List[str] = Field(
        default_factory=list, description="선호 식당 아이디 리스트"
    )
    dislikes: List[str] = Field(
        default_factory=list, description="비선호 식당 아이디 리스트"
    )


class HumanVotes(BaseModel):
    """사용자(Human) 투표 결과"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    likes: List[str] = Field(
        default_factory=list, description="선호 식당 아이디 리스트"
    )
    dislikes: List[str] = Field(
        default_factory=list, description="비선호 식당 아이디 리스트"
    )


class UserPersonaPhase(BaseModel):
    """각 페이즈별 사용자 페르소나 상태"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    user_id: str = Field(..., description="사용자 아이디")
    base_persona: str = Field(..., description="기본 페르소나 특징")
    opinion: str = Field(
        ...,
        alias="현재 페르소나의 식당에 대한 의견",
        description="새로운 페르소나 특징/의견",
    )

    current_llm_votes: LLMVotes = Field(..., description="현재 라운드 LLM 투표")
    next_human_votes: HumanVotes = Field(..., description="다음 라운드 사용자 투표")


class ProcessedRestaurant(BaseModel):
    """처리된 식당 정보 (후보군/제공됨)"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    restaurant_id: str = Field(..., description="식당 아이디")
    filtered_score: float = Field(..., description="필터링 점수")


class Phase(BaseModel):
    """추천 프로세스 페이즈 (라운드) 정보"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    round: int = Field(..., description="라운드 번호")
    refresh_reason: str = Field(default="", description="새로고침/재추천 사유")

    user_persona: List[UserPersonaPhase] = Field(
        default_factory=list, description="참여자 페르소나 목록"
    )
    served_restaurants: List[ProcessedRestaurant] = Field(
        default_factory=list, description="이 라운드에 제공된 식당 목록"
    )

    created_at: datetime = Field(
        default_factory=datetime.now, description="페이즈 생성 시간"
    )


class DiningProcessDocument(BaseModel):
    """MongoDB 'dining_process' 컬렉션 문서 모델 (추천 진행 과정 저장)"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    # _id: str (MongoDB 자동생성)

    dining_id: str = Field(..., description="회식 아이디")
    groups_id: str = Field(..., description="그룹 아이디")
    dining_date: datetime = Field(..., description="회식 날짜")
    budget: int = Field(..., description="회식 예산")

    x: str = Field(..., description="경도")
    y: str = Field(..., description="위도")

    current_phase: int = Field(default=1, description="현재 진행 중인 페이즈(라운드)")
    is_completed: bool = Field(default=False, description="추천 프로세스 완료 여부")

    phases: List[Phase] = Field(default_factory=list, description="라운드별 기록")

    restaurant_candidate: List[ProcessedRestaurant] = Field(
        default_factory=list, description="전체 식당 후보군 (필터링 후)"
    )
    final_restaurant: List[str] = Field(
        default_factory=list, description="최종 선정된 식당 아이디 목록"
    )

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
