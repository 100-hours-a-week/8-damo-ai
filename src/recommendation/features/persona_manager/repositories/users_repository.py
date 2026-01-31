from typing import Optional
from src.shared.database import get_db
from src.recommendation.features.persona_manager.entities.users import Users


class UsersRepository:
    def __init__(self):
        self.collection_name = "users"

    def _get_collection(self):
        return get_db()[self.collection_name]

    async def save(self, user: Users) -> Users:
        """
        페르소나 문서를 저장하거나 업데이트합니다.
        user_id(id)를 기준으로 식별합니다.
        """
        collection = self._get_collection()

        await collection.replace_one(
            {"id": user.id}, user.model_dump(by_alias=True), upsert=True
        )
        return user

    async def find_by_user_id(self, user_id: int) -> Optional[Users]:
        collection = self._get_collection()
        data = await collection.find_one({"id": user_id})
        if data:
            return Users(**data)
        return None
