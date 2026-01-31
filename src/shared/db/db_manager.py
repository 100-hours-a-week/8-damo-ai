import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne, errors, GEOSPHERE, ReturnDocument
from typing import List, Dict, Any, Optional, Union
from src.core.config import settings
from src.recommendation.schemas.recommendations_request import RecommendationsRequest
from src.recommendation.workflows.states.recommendation_state import RecommendationState


class MongoManager:
    def __init__(self, uri: str = None, db_name: str = None, col_name: str = ""):
        # 설정을 런타임에 참조하도록 변경 (테스트 환경 대응)
        current_uri = uri or settings.MONGODB_URI
        current_db_name = db_name or settings.DB_NAME

        # 1. 비동기 클라이언트 생성
        self.client = AsyncIOMotorClient(current_uri)
        self.db = self.client[current_db_name]
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

    async def read_all(
        self, query: Dict[str, Any] = {}, limit: int = 0
    ) -> List[Dict[str, Any]]:
        # motor에서는 find() 호출 후 to_list()를 명시적으로 호출해야 합니다.
        cursor = self.collection.find(query).limit(limit)
        return await cursor.to_list(length=None)

    async def read_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # await 추가
        return await self.collection.find_one(query)

    async def update_phase_count(
        self, filter_query: Dict[str, Any], field_name: str
    ) -> Optional[Dict[str, Any]]:
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
                return_document=ReturnDocument.AFTER,  # 업데이트가 완료된 후의 데이터를 가져옴
            )
            return result
        except errors.PyMongoError as e:
            print(f"단계 업데이트 에러: {e}")
            return None

    async def update_one(
        self, filter_query: Dict[str, Any], update_data: Dict[str, Any]
    ) -> int:
        """하나의 문서 수정 ($set 연산자 사용)"""
        result = await self.collection.update_one(filter_query, {"$set": update_data})
        return result.modified_count

    async def find_by_location(
        self, longitude: float, latitude: float, max_distance: int = 5000
    ) -> List[Dict[str, Any]]:
        """
        주어진 좌표를 기준으로 반경 내의 식당 목록을 거리순으로 조회합니다.
        (motor 비동기 방식 적용)
        """
        if self.collection is None:
            raise ValueError(
                "컬렉션이 설정되지 않았습니다. set_collection()을 호출하세요."
            )
        query = {
            "location": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [longitude, latitude],
                    },
                    "$maxDistance": max_distance,
                }
            }
        }

        # motor 방식: find() 후 to_list() 사용
        cursor = self.collection.find(query)
        return await cursor.to_list(length=None)

    # 회식 세션을 저장하는 함수
    async def save_dining_session(self, result: RecommendationState):
        """
        추천 결과를 dining_sessions 컬렉션에 저장 또는 업데이트합니다.
        1. 데이터가 들어오면 diningId 기반으로 문서를 검색한다.
        1-1. (문서가 있을 경우) 특정 항목을 업데이트한다. (후보 리스트 및 업데이트 시간)
        1-2. (문서가 없을 경우) 새로운 문서를 만든다.
        """
        try:
            # 컬렉션 전환
            self.set_collection("dining_sessions")

            user_ids = result.get("user_ids")
            dining_data = result.get("dining_data")
            restaurant_candidates = result.get("filtered_restaurants")
            rejected_candidates = result.get("rejected_restaurants")
            phases = result.get("vote_result_list")
            status_message = result.get("status_message")

            if dining_data is None:
                print("세션 저장 실패: dining_data가 없습니다.")
                return False

            # 1. dining_info 추출 (Pydantic 모델 또는 dict 대응)
            if hasattr(dining_data, "model_dump"):  # Pydantic v2
                dining_info = dining_data.model_dump()
            elif hasattr(dining_data, "dict"):  # Pydantic v1
                dining_info = dining_data.dict()
            elif isinstance(dining_data, dict):
                dining_info = dining_data
            else:
                dining_info = {}

            # 2. dining_id 확보 (state direct -> info 순서)
            dining_id = result.get("dining_id")
            if dining_id is None:
                dining_id = dining_info.get("diningId") or dining_info.get("dining_id")
            if dining_id is None:
                print("세션 저장 실패: diningId를 찾을 수 없습니다.")
                return False

            # 문서 검색 (diningId 기준)
            existing = await self.read_one({"diningId": dining_id})
            now = datetime.now()

            if existing:
                # 있을 경우 (UPDATE)
                update_query = {
                    "$set": {
                        "userIds": user_ids,
                        "restaurantCandidate": restaurant_candidates,
                        "phases": phases,
                        "updatedAt": now,
                    },
                    "$push": {"statusMessage": {"$each": status_message}},
                }

                # 거절된 식당이 있으면 push ($each 사용으로 리스트 병합)
                if rejected_candidates:
                    update_query["$push"]["rejectedCandidate"] = {
                        "$each": rejected_candidates
                    }

                await self.collection.update_one({"diningId": dining_id}, update_query)
                await self.update_phase_count({"diningId": dining_id}, "currentPhase")
            else:
                # 없을 경우 (CREATE)
                session_data = {
                    "userIds": user_ids,
                    "diningId": dining_id,
                    "budget": dining_info.get("budget"),
                    "currentPhase": 1,
                    "diningDate": dining_info.get("diningDate")
                    or dining_info.get("dining_date"),
                    "finalRestaurant": None,
                    "groupsId": dining_info.get("groupsId")
                    or dining_info.get("groups_id"),
                    "isCompleted": False,
                    "phases": phases,
                    "restaurantCandidate": restaurant_candidates,
                    "rejectedCandidate": [],
                    "statusMessage": status_message,
                    "x": dining_info.get("x"),
                    "y": dining_info.get("y"),
                    "createdAt": now,
                    "updatedAt": now,
                }
                await self.create_one(session_data)

            return True
        except Exception as e:
            print(f"세션 저장 중 오류 발생: {str(e)}")
            return False
