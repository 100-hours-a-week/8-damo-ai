from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import List, Optional


class BusinessHour(BaseModel):
    """영업 시간 모델"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    day: str = Field(..., description="요일 (예: 월, 화, 수...)")
    time: str = Field(..., description="영업 시간 (예: 16:30 - 02:00)")
    last_order: str = Field(default="", description="라스트 오더 시간")


class Menu(BaseModel):
    """식당 메뉴 정보 모델"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: str = Field(..., description="메뉴 이름")
    price: Optional[int] = Field(default=None, description="메뉴 가격")
    description: str = Field(default="", description="메뉴 상세 설명")
    image_url: List[str] = Field(default_factory=list, description="메뉴 이미지 URL 리스트")


class ReviewKeyword(BaseModel):
    """식당 리뷰 분석 키워드 모델"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    keyword: str = Field(..., description="키워드 내용")
    count: int = Field(..., description="키워드 언급 빈도/횟수")


class Restaurant(BaseModel):
    """식당 전체 정보 모델"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    address_name: str = Field(..., description="지번 주소")
    category_group_name: str = Field(..., description="카테고리 그룹 이름 (예: 음식점)")
    category_detail: str = Field(..., description="상세 업종 카테고리 (예: 치킨)")
    phone: str = Field(default="", description="전화번호")
    place_name: str = Field(..., description="식당 이름")
    place_url: str = Field(..., description="카카오맵 상세 페이지 URL")
    road_address_name: str = Field(..., description="도로명 주소")
    x: str = Field(..., description="경도 (longitude)")
    y: str = Field(..., description="위도 (latitude)")
    review_count: int = Field(default=0, description="리뷰 총 개수")
    review_ids: List[str] = Field(default_factory=list, description="리뷰 PK 리스트")
    is_naver_available: bool = Field(default=False, description="네이버 예약/정보 가용 여부")
    naver_url: str = Field(default="", description="네이버 플레이스 URL")
    shop_url: str = Field(default="", description="매장 홈페이지 URL")
    business_hour: List[BusinessHour] = Field(
        default_factory=list, description="요일별 영업 시간 리스트"
    )
    amenities: List[str] = Field(default_factory=list, description="편의 시설 정보 (예: 주차, 포장)")
    menu_count: int = Field(default=0, description="등록된 메뉴 총 개수")
    menus: List[Menu] = Field(default_factory=list, description="메뉴 상세 정보 리스트")
    restaurant_review_keywords: List[ReviewKeyword] = Field(
        default_factory=list, description="네이버/카카오 리뷰 키워드 통계 리스트"
    )
