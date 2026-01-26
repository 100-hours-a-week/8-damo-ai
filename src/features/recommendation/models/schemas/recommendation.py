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
    
    id: int = Field(..., description="회식 테이블의 PK (snowflake)", json_schema_extra={"example": 1234567890})
    groups_id: int = Field(..., description="그룹 테이블의 PK")
    dining_date: datetime = Field(..., description="회식 진행 날짜")
    vote_due_date: datetime = Field(..., description="투표 마감 날짜")
    budget: int = Field(..., description="회식 진행 예산")
    created_at: datetime = Field(..., description="생성 일시")

# RecommendedItem
class RecommendedItem(BaseModel):
    """추천 식당 아이템"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    
    restaurant_id: str = Field(..., description="식당 식별자")
    restaurant_name: str = Field(..., description="식당 이름")
    reasoning_description: str = Field(..., max_length=500, description="추천 사유")
    # restaurant_phone: str = Field(..., description="식당 전화번호")
    # is_naver_available: bool = Field(..., description="네이버 예약 가능 여부")
    # naver_url: str = Field(..., description="네이버 플레이스 URL")
    # address_name: str = Field(..., description="전체 지번 주소")
    # road_address_name: str = Field(..., description="전체 도로명 주소")
    # 응답 데이터를 백엔드와 논의해서 책임 소재를 확실히 할것

# Recommendation Request
class RecommendationRequest(BaseModel):
    """
    추천을 위한 사용자 데이터 요청 모델입니다.
    회식 데이터와 사용자 데이터를 함께 전달받아 처리합니다.
    """
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    dining_data: DiningData = Field(..., description="회식 데이터")
    user_data: List[UserData] = Field(..., description="추천할 사용자 데이터 리스트")

# Recommendation Response
class RecommendationResponse(BaseModel):
    """
    추천 결과 응답 모델입니다.
    처리 결과 상태와 소요 시간, 추천 식당 정보 상위 5개를 포함합니다.
    """
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    success: bool = Field(..., description="API 호출 성공 여부 (true: 성공, false: 실패)")
    process_time: float = Field(..., description="서버 측 API 처리 소요 시간 (초 단위)")
    recommended_items: List[RecommendedItem] = Field(..., description="추천 식당 정보 상위 5개")

# Analyze Refresh Request
class AnalyzeRefreshRequest(RecommendationRequest):
    """
    재추천을 위한 사용자 데이터 요청 모델입니다.
    회식 데이터와 사용자 데이터를 함께 전달받아 처리합니다.
    """
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    refresh_count: int = Field(..., description="재추천 횟수")

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

# Analyze Refresh Request
class AnalyzeRefreshRequest(RecommendationRequest):
    """
    재추천을 위한 사용자 데이터 요청 모델입니다.
    회식 데이터와 사용자 데이터를 함께 전달받아 처리합니다.
    """
    refresh_count: int = Field(..., description="재추천 횟수")
    # 식당 정보를 주고 받을때 백엔드로부터 받을지 아니면 mongo에 저장해서 추천/비추천으로 판단할지 논의 후 결정 필요