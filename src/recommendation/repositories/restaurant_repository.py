from typing import Optional, List
from src.shared.database import get_db
from src.recommendation.entities.restaurant import RestaurantDocument


class RestaurantRepository:
    """Restaurant 컬렉션에 대한 데이터 접근 계층"""

    def __init__(self):
        self.collection_name = "restaurants"

    def _get_collection(self):
        return get_db()[self.collection_name]

    async def find_by_id(self, restaurant_id: str) -> Optional[RestaurantDocument]:
        """
        restaurant_id로 식당 정보를 조회합니다.

        Args:
            restaurant_id: 식당 ID

        Returns:
            RestaurantDocument 또는 None
        """
        collection = self._get_collection()
        # ID가 ObjectId인지 str인지 확인 필요하지만, 여기서는 저장된 형식(str)을 따른다고 가정
        data = await collection.find_one({"_id": restaurant_id})
        if data:
            return RestaurantDocument(**data)
        return None

    async def find_by_ids(self, restaurant_ids: List[str]) -> List[RestaurantDocument]:
        """
        여러 restaurant_id로 식당 정보를 일괄 조회합니다.

        Args:
            restaurant_ids: 식당 ID 리스트

        Returns:
            RestaurantDocument 리스트
        """
        collection = self._get_collection()
        cursor = collection.find({"_id": {"$in": restaurant_ids}})

        restaurants = []
        async for data in cursor:
            restaurants.append(RestaurantDocument(**data))

        return restaurants
