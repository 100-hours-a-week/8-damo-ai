from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.shared.database import get_db
from src.recommendation.entities.persona import Persona


class PersonaRepository:
    def __init__(self, db: AsyncIOMotorDatabase = None):
        self.db = db or get_db()
        self.collection = self.db["personas"]

    async def save(self, persona: Persona) -> bool:
        """
        페르소나 정보를 저장하거나 업데이트합니다.
        id를 기준으로 upsert 수행.
        """
        # by_alias=True: Persona 모델의 alias_generator(to_camel) 설정에 따라 필드명 변환
        persona_dict = persona.model_dump(by_alias=True)

        # upsert 수행
        result = await self.collection.update_one(
            {"id": persona.id}, {"$set": persona_dict}, upsert=True
        )
        return result.acknowledged

    async def find_by_id(self, user_id: int) -> Optional[Persona]:
        """ID로 페르소나 조회"""
        doc = await self.collection.find_one({"id": user_id})
        if doc:
            return Persona.model_validate(doc)
        return None

    async def get_all(self) -> List[Persona]:
        """모든 페르소나 조회"""
        cursor = self.collection.find()
        results = await cursor.to_list(length=None)
        return [Persona.model_validate(doc) for doc in results]
