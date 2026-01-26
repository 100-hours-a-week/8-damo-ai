from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import List, Optional, TypedDict, Annotated
import operator
from datetime import datetime
from src.features.recommendation.models.enums import AllergyType, Gender, AgeGroup, DislikeType, OnboardingStatus

# UserData Request
class UserData(BaseModel):
    """사용자 데이터 모델(사용자 특이사항은 별도의 mongoDB에서 조회)"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int = Field(..., description="사용자 테이블의 PK (snowflake)", json_schema_extra={"example": 123456789})
    email: str = Field(..., max_length=100, description="소셜 가입 계정 이메일(성향을 분석하기 위함)")
    nickname: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=10, 
        pattern=r'^[^\s!@#$%^&*(),.?":{}|<>]*$',
        description="닉네임 (1-10자, 공백 및 특수문자 금지)"
    )
    gender: Optional[Gender] = Field(None, description="성별 (MALE, FEMALE)")
    age_group: Optional[AgeGroup] = Field(None, description="연령대")
    is_push_notification_allowed: Optional[bool] = Field(None, description="푸시 알림 허용 여부(계획적인지 아닌지)")
    onboarding_status: Optional[OnboardingStatus] = Field(None, description="온보딩 상태 (BASIC, CHARACTERISTIC, DONE)")
    created_at: Optional[datetime] = Field(None, description="생성 일시")
    updated_at: Optional[datetime] = Field(None, description="수정 일시")
    withdraw_at: Optional[datetime] = Field(None, description="사용자 탈퇴 일시")
    is_withdraw: Optional[bool] = Field(None, description="탈퇴 여부")
    allergies: Optional[List[AllergyType]] = Field(None, description="알레르기 정보 목록")
    
    dislikes: Optional[List[DislikeType]] = Field(None, description="비선호 음식 정보 목록")

# UserData Request
class UserDataRequest(BaseModel):
    """
    페르소나 업데이트를 위한 사용자 데이터 요청 모델입니다.
    여러 명의 사용자 데이터를 한 번에 보낼 수 있도록 리스트 구조를 가집니다.
    """
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    user_data: List[UserData] = Field(..., description="업데이트할 사용자 데이터 리스트")

# UserData Response
class UserDataResponse(BaseModel):
    """
    페르소나 업데이트 결과 응답 모델입니다.
    처리 결과 상태와 소요 시간, 대상 사용자 ID를 포함합니다.
    """
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    success: bool = Field(..., description="API 호출 성공 여부 (true: 성공, false: 실패)")
    process_time: float = Field(..., description="서버 측 API 처리 소요 시간 (초 단위)")
    user_id: int = Field(..., description="성공적으로 처리된 사용자의 고유 ID (Snowflake ID)")

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

