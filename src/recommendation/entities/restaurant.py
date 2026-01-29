from typing import List, Optional
from pydantic.alias_generators import to_camel
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


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
    image_url: List[str] = Field(
        default_factory=list, description="메뉴 이미지 URL 리스트"
    )


class RestaurantDocument(BaseModel):
    """MongoDB 'restaurants' 컬렉션 문서 모델"""

    model_config = ConfigDict(
        populate_by_name=True
    )  # DB 필드명 그대로 사용 (snake_case)

    # MongoDB _id 매핑
    id: Optional[str] = Field(alias="_id", default=None)

    place_name: str
    address_name: str
    road_address_name: str
    category_group_name: str
    category_detail: str
    phone: str = ""
    place_url: str
    x: str
    y: str

    review_count: int = 0
    review_ids: List[str] = Field(default_factory=list)
    is_naver_available: bool = False
    naver_url: str = ""
    shop_url: str = ""

    # 상세 정보 - Embedded Document
    menus: List[Menu] = Field(default_factory=list)
    business_hour: List[BusinessHour] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)

    # 메타 정보
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


def to_camel(string: str) -> str:
    return string
