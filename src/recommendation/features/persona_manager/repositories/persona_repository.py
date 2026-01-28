from typing import Optional
from src.shared.database import get_db
from src.recommendation.features.persona_manager.entities.persona import PersonaDocument


class PersonaRepository:
    def __init__(self):
        self.collection_name = "users"

    def _get_collection(self):
        return get_db()[self.collection_name]

    async def save(self, persona: PersonaDocument) -> PersonaDocument:
        """
        페르소나 문서를 저장하거나 업데이트합니다.
        nickname(또는 user_id)을 기준으로 식별한다고 가정합니다.
        현재 PersonaDocument에는 명시적인 user_id 필드가 없으므로 nickname을 식별자로 사용하는 예시입니다.
        실제 비즈니스 로직에 맞춰 user_id 추가가 필요할 수 있습니다.
        """
        collection = self._get_collection()

        # TODO: user_id 필드가 생긴다면 {"user_id": persona.user_id} 로 변경
        result = await collection.replace_one(
            {"nickname": persona.nickname},
            persona.model_dump(by_alias=True),
            upsert=True,
        )
        return persona

    async def find_by_nickname(self, nickname: str) -> Optional[PersonaDocument]:
        collection = self._get_collection()
        data = await collection.find_one({"nickname": nickname})
        if data:
            return PersonaDocument(**data)
        return None
