"""식당 후보 데이터 스키마

MongoDB에서 조회된 식당 데이터의 타입 정의입니다.
"""

from typing import List, Optional, TypedDict, Any


class Location(TypedDict):
    """위치 정보"""

    distance_score: float
    distance: int
    budget_score: float
    total_score: float


class Menu(TypedDict):
    """메뉴 정보"""

    name: str
    price: Optional[int]
    description: Optional[str]


class RestaurantCandidate(TypedDict):
    """식당 후보 데이터 스키마

    MongoDB에서 조회된 식당 정보를 담는 TypedDict입니다.
    """

    _id: str  # MongoDB ObjectId
    address_name: str  # 지번 주소
    category_group_name: str  # 카테고리 그룹 (예: "음식점")
    category_detail: str  # 상세 카테고리 (예: "베트남음식")
    phone: str  # 전화번호
    place_name: str  # 식당 이름
    place_url: str  # 카카오맵 URL
    road_address_name: str  # 도로명 주소
    x: str  # 경도
    y: str  # 위도
    review_count: int  # 리뷰 수
    review_ids: List[str]  # 리뷰 ID 목록
    is_naver_available: bool  # 네이버 지도 사용 가능 여부
    naver_url: str  # 네이버 지도 URL
    shop_url: str  # 쇼핑몰 URL
    business_hour: List[str]  # 영업시간
    amenities: List[str]  # 편의시설
    menu_count: int  # 메뉴 수
    menus: List[Any]  # 메뉴 목록 (상세 타입은 Menu)
    restaurant_review_keywords: List[str]  # 리뷰 키워드
    location: Location  # 위치 및 점수 정보


def format_restaurant_for_display(restaurant: RestaurantCandidate) -> str:
    """식당 정보를 사람이 읽기 쉬운 형태로 포맷팅

    Args:
        restaurant: 식당 후보 데이터

    Returns:
        포맷팅된 문자열
    """
    # 주소 간소화 (도로명 주소 우선)
    address = restaurant.get("road_address_name") or restaurant.get(
        "address_name", "주소 없음"
    )

    # 거리 정보
    distance = restaurant.get("location", {}).get("distance", 0)
    distance_text = f"{distance}m" if distance < 1000 else f"{distance / 1000:.1f}km"

    # 리뷰 키워드 (상위 3개)
    keywords = restaurant.get("restaurant_review_keywords", [])[:3]
    keywords_text = ", ".join(keywords) if keywords else "키워드 없음"

    # 메뉴 정보 (상위 3개)
    menus = restaurant.get("menus", [])[:3]
    menu_names = [m.get("name", "메뉴") for m in menus if isinstance(m, dict)]
    menus_text = ", ".join(menu_names) if menu_names else "메뉴 정보 없음"

    return f"""
📍 {restaurant.get("place_name", "식당 이름 없음")}
   - 카테고리: {restaurant.get("category_detail", "N/A")}
   - 위치: {address} ({distance_text})
   - 리뷰: {restaurant.get("review_count", 0)}개
   - 키워드: {keywords_text}
   - 대표 메뉴: {menus_text}
   - 전화: {restaurant.get("phone", "정보 없음")}
    """.strip()


def format_restaurants_for_prompt(restaurants: List[RestaurantCandidate]) -> str:
    """여러 식당 정보를 프롬프트용으로 포맷팅

    Args:
        restaurants: 식당 후보 목록

    Returns:
        프롬프트에 사용할 포맷팅된 문자열
    """
    if not restaurants:
        return "후보 식당 없음"

    formatted = []
    for i, restaurant in enumerate(restaurants, 1):
        name = restaurant.get("place_name", "Unknown")
        category = restaurant.get("category_detail", "N/A")
        address = restaurant.get("road_address_name") or restaurant.get(
            "address_name", "주소 없음"
        )
        distance = restaurant.get("location", {}).get("distance", 0)
        distance_text = (
            f"{distance}m" if distance < 1000 else f"{distance / 1000:.1f}km"
        )
        review_count = restaurant.get("review_count", 0)
        keywords = restaurant.get("restaurant_review_keywords", [])[:3]
        keywords_text = ", ".join(keywords) if keywords else "없음"

        formatted.append(
            f"{i}. **{name}** (ID: {restaurant.get('_id', 'unknown')})\n"
            f"   - 카테고리: {category}\n"
            f"   - 위치: {address} ({distance_text})\n"
            f"   - 리뷰: {review_count}개\n"
            f"   - 키워드: {keywords_text}"
        )

    return "\n\n".join(formatted)


def get_restaurant_id(restaurant: RestaurantCandidate) -> str:
    """식당 ID 추출

    Args:
        restaurant: 식당 후보 데이터

    Returns:
        식당 ID (_id 또는 place_name)
    """
    return restaurant.get("_id") or restaurant.get("place_name", "unknown")


def get_restaurant_name(restaurant: RestaurantCandidate) -> str:
    """식당 이름 추출

    Args:
        restaurant: 식당 후보 데이터

    Returns:
        식당 이름
    """
    return restaurant.get("place_name", "Unknown Restaurant")


def get_restaurant_category(restaurant: RestaurantCandidate) -> str:
    """식당 카테고리 추출

    Args:
        restaurant: 식당 후보 데이터

    Returns:
        카테고리 (상세 카테고리 우선)
    """
    return restaurant.get("category_detail") or restaurant.get(
        "category_group_name", "N/A"
    )


def get_restaurant_location(restaurant: RestaurantCandidate) -> str:
    """식당 위치 추출

    Args:
        restaurant: 식당 후보 데이터

    Returns:
        위치 (도로명 주소 우선)
    """
    return restaurant.get("road_address_name") or restaurant.get("address_name", "N/A")
