import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne, errors, GEOSPHERE, ReturnDocument
from typing import List, Dict, Any, Optional, Union
from src.core.config import settings
from src.recommendation.schemas.recommendations_request import RecommendationsRequest

class MongoManager:
    def __init__(self, uri: str = settings.MONGODB_URI, db_name: str = settings.DB_NAME, col_name: str = ""):
        # 1. 비동기 클라이언트 생성
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db[col_name] if col_name else None

    def set_collection(self, col_name: str):
        """런타임에 컬렉션을 교체해야 할 경우 사용"""
        self.collection = self.db[col_name]

    async def create_one(self, data: Dict[str, Any]):
        try:
            # await 추가
            result = await self.collection.insert_one(data)
            return result.inserted_id
        except errors.PyMongoError as e:
            print(f"삽입 에러: {e}")
            return None

    async def read_all(self, query: Dict[str, Any] = {}, limit: int = 0) -> List[Dict[str, Any]]:
        # motor에서는 find() 호출 후 to_list()를 명시적으로 호출해야 합니다.
        cursor = self.collection.find(query).limit(limit)
        return await cursor.to_list(length=None)

    async def read_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # await 추가
        return await self.collection.find_one(query)

    async def update_phase_count(self, filter_query: Dict[str, Any], field_name: str) -> Optional[Dict[str, Any]]:
        """
        특정 필드(field_name)의 값을 1 증가시키고, 업데이트된 문서를 반환합니다.
        
        Args:
            filter_query: 대상을 찾기 위한 쿼리 (예: {"diningId": "..."})
            field_name: 1을 더할 필드명 (예: "currentPhase")
            
        Returns:
            업데이트된 후의 문서 데이터 (Dict)
        """
        try:
            result = await self.collection.find_one_and_update(
                filter_query,
                {"$inc": {field_name: 1}},
                return_document=ReturnDocument.AFTER  # 업데이트가 완료된 후의 데이터를 가져옴
            )
            return result
        except errors.PyMongoError as e:
            print(f"단계 업데이트 에러: {e}")
            return None

    async def update_one(self, filter_query: Dict[str, Any], update_data: Dict[str, Any]) -> int:
        """하나의 문서 수정 ($set 연산자 사용)"""
        result = await self.collection.update_one(filter_query, {"$set": update_data})
        return result.modified_count

    async def find_by_location(self, longitude: float, latitude: float, max_distance: int = 5000) -> List[Dict[str, Any]]:
        """
        주어진 좌표를 기준으로 반경 내의 식당 목록을 거리순으로 조회합니다.
        (motor 비동기 방식 적용)
        """
        if self.collection is None:
            raise ValueError("컬렉션이 설정되지 않았습니다. set_collection()을 호출하세요.")
        query = {
            "location": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [longitude, latitude]
                    },
                    "$maxDistance": max_distance
                }
            }
        }

        # motor 방식: find() 후 to_list() 사용
        cursor = self.collection.find(query)
        return await cursor.to_list(length=None)

    # 회식 세션을 저장하는 함수
    async def save_dining_session(self, request: RecommendationsRequest, filtered_restaurants: List[Dict[str, Any]], iteration_count: int):
        """
        추천 결과를 dining_sessions 컬렉션에 저장 또는 업데이트합니다.
        """
        try:
            self.set_collection("dining_sessions")
            
            session_data = {
                "diningId": request.dining_data.dining_id,
                "budget": request.dining_data.budget,
                "currentPhase": iteration_count + 1,
                "diningDate": request.dining_data.dining_date,
                "finalRestaurant": None,
                "groupsId": request.dining_data.groups_id,
                "isCompleted": False,
                "phases": [],
                "restaurantCandidate": filtered_restaurants, # 상위 5개 저장
                "x": request.dining_data.x,
                "y": request.dining_data.y
            }
            
            # diningId 기준 Upsert
            await self.collection.update_one(
                {"diningId": request.dining_data.dining_id},
                {"$set": session_data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"세션 저장 중 오류 발생: {str(e)}")
            return False