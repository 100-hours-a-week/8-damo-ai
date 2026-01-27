from src.recommendation.schemas.requests.recommendation_request import RecommendedItem

MOCK_DEV_ITEMS = [
    RecommendedItem(
        restaurant_id="6976b54010e1fa815903d4ce",
        reasoning_description="사용자의 알레르기 수칙을 준수하며 평점이 높습니다.",
    ),
    RecommendedItem(
        restaurant_id="6976b57f10e1fa815903d4cf",
        reasoning_description="새로운 분위기의 식당으로 재추천되었습니다.",
    ),
    RecommendedItem(
        restaurant_id="6976b58610e1fa815903d4d0",
        reasoning_description="가격이 저렴하며 리뷰가 많습니다.",
    ),
    RecommendedItem(
        restaurant_id="6976b8b9fb8d6fe1764695b6",
        reasoning_description="특별한 메뉴가 있는 식당으로 추천되었습니다.",
    ),
    RecommendedItem(
        restaurant_id="6976b8bafb8d6fe1764695b7",
        reasoning_description="가족과 함께 즐길 수 있는 식당으로 추천되었습니다.",
    ),
]
