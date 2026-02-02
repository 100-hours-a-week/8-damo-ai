import pytest
import asyncio
from datetime import datetime
from src.recommendation.features.persona_manager.repositories.users_repository import (
    UsersRepository,
)
from src.recommendation.features.persona_manager.entities.users import Users
from src.recommendation.enums import Gender, AgeGroup, AllergyType


@pytest.mark.asyncio
async def test_save_and_find_user():
    # Repository 인스턴스 생성
    repository = UsersRepository()

    # 테스트용 데이터 생성
    # user_id는 int 타입이어야 함
    test_user_id = int(datetime.now().timestamp())
    test_nickname = f"test_user_{test_user_id}"

    user = Users(
        id=test_user_id,
        nickname=test_nickname,
        gender=Gender.MALE,
        age_group=AgeGroup.TWENTIES,
        allergies=[AllergyType.PEACH, AllergyType.CRAB],
        like_foods=["KOREAN"],
        like_ingredients=["KOREAN"],
        other_characteristics="Integration Test User",
        base_persona="Friendly foodie",
    )

    print(f"\n[Test] Saving user with nickname: {test_nickname}")

    # 저장 테스트
    saved_user = await repository.save(user)
    assert saved_user.nickname == test_nickname

    print(f"[Test] Successfully saved. Now retrieving...")

    # 조회 테스트
    found_user = await repository.find_by_user_id(test_user_id)

    assert found_user is not None
    assert found_user.id == test_user_id
    assert found_user.nickname == test_nickname
    assert found_user.gender == Gender.MALE
    assert AllergyType.PEACH in found_user.allergies

    print(f"[Test] Successfully retrieved user: {found_user.id}")
