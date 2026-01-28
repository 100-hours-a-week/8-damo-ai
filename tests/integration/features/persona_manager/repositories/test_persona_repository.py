import pytest
import asyncio
from datetime import datetime
from src.recommendation.features.persona_manager.repositories.persona_repository import (
    PersonaRepository,
)
from src.recommendation.features.persona_manager.entities.persona import PersonaDocument
from src.recommendation.enums.user_enums import Gender, AgeGroup, AllergyType


@pytest.mark.asyncio
async def test_save_and_find_persona():
    # Repository 인스턴스 생성
    repository = PersonaRepository()

    # 테스트용 데이터 생성 (Unique한 닉네임 사용)
    test_nickname = f"test_user_{int(datetime.now().timestamp())}"

    persona = PersonaDocument(
        id=99999,
        nickname=test_nickname,
        gender=Gender.MALE,
        age_group=AgeGroup.TWENTIES,
        allergies=[AllergyType.PEACH, AllergyType.CRAB],
        like_food_categories_id=["KOREAN"],
        categories_id=["KOREAN"],
        other_characteristics="Integration Test User",
        base_persona="Friendly foodie",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    print(f"\n[Test] Saving persona with nickname: {test_nickname}")

    # 저장 테스트
    saved_persona = await repository.save(persona)
    assert saved_persona.nickname == test_nickname

    print(f"[Test] Successfully saved. Now retrieving...")

    # 조회 테스트
    found_persona = await repository.find_by_user_id(99999)

    assert found_persona is not None
    assert found_persona.id == 99999
    assert found_persona.nickname == test_nickname
    assert found_persona.gender == Gender.MALE
    assert AllergyType.PEACH in found_persona.allergies

    print(f"[Test] Successfully retrieved persona: {found_persona.id}")
