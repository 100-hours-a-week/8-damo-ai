import pytest
from datetime import datetime

from src.recommendation.features.persona_manager.services.persona_service import (
    PersonaService,
)
from src.recommendation.schemas.update_persona_db_request import UpdatePersonaDBRequest
from src.recommendation.schemas.user_data import UserData
from src.recommendation.schemas.review_data import ReviewData
from src.recommendation.enums import Gender, AgeGroup, AllergyType


@pytest.mark.asyncio
@pytest.mark.integration
async def test_persona_service_end_to_end():
    """
    PersonaService의 전체 플로우 통합 테스트
    실제 DB와 LLM을 사용하여 페르소나 생성 및 저장을 테스트합니다.
    """
    # 테스트용 고유 사용자 ID 생성
    test_user_id = int(datetime.now().timestamp())

    # 테스트 데이터 준비
    user_data = UserData(
        id=test_user_id,
        nickname=f"integration_test_user_{test_user_id}",
        gender=Gender.FEMALE,
        age_group=AgeGroup.THIRTIES,
        allergies=[AllergyType.SHRIMP, AllergyType.CRAB],
        like_food_categories_id=["ITALIAN", "KOREAN"],
        categories_id=["PASTA", "KOREAN"],
        other_characteristics="Prefers cozy and romantic atmosphere",
    )

    # 실제 DB에 존재하는 restaurant_id를 사용해야 함
    # 여기서는 테스트용 리뷰 데이터 생성 (실제 환경에서는 DB에 있는 ID 사용)
    review_data = [
        ReviewData(
            restaurant_id="test_rest_001",
            user_id=test_user_id,
            rating=5,
            comment="파스타가 정말 맛있었어요. 분위기도 로맨틱하고 좋았습니다.",
        ),
        ReviewData(
            restaurant_id="test_rest_002",
            user_id=test_user_id,
            rating=4,
            comment="한식당인데 깔끔하고 맛있어요. 재방문 의사 있습니다.",
        ),
        ReviewData(
            restaurant_id="test_rest_003",
            user_id=test_user_id,
            rating=3,
            comment="음식은 괜찮았지만 조금 시끄러웠어요.",
        ),
    ]

    request = UpdatePersonaDBRequest(
        user_data=user_data,
        review_data=review_data,
    )

    # PersonaService 실행
    service = PersonaService()

    try:
        result = await service.create_and_save_persona(request)

        # 결과 검증
        assert result is not None
        assert result.id == test_user_id
        assert result.nickname == f"integration_test_user_{test_user_id}"
        assert result.gender == Gender.FEMALE
        assert result.age_group == AgeGroup.THIRTIES
        assert AllergyType.SHRIMP in result.allergies
        assert AllergyType.CRAB in result.allergies
        assert "ITALIAN" in result.like_food_categories_id
        assert "KOREAN" in result.like_food_categories_id

        # 페르소나가 생성되었는지 확인
        assert result.base_persona is not None
        assert len(result.base_persona) > 0

        print(f"\n[Integration Test] 생성된 페르소나:")
        print(f"User ID: {result.id}")
        print(f"Nickname: {result.nickname}")
        print(f"Base Persona: {result.base_persona[:200]}...")

        # DB에서 다시 조회하여 저장 확인
        from src.recommendation.features.persona_manager.repositories.persona_repository import (
            PersonaRepository,
        )

        repo = PersonaRepository()
        saved_persona = await repo.find_by_user_id(test_user_id)

        assert saved_persona is not None
        assert saved_persona.id == test_user_id
        assert saved_persona.base_persona == result.base_persona

        print(f"[Integration Test] DB 조회 성공: {saved_persona.nickname}")

    except Exception as e:
        pytest.fail(f"Integration test failed: {str(e)}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_persona_service_with_no_reviews():
    """
    리뷰가 없는 경우의 페르소나 생성 테스트
    """
    test_user_id = int(datetime.now().timestamp()) + 1000

    user_data = UserData(
        id=test_user_id,
        nickname=f"no_review_user_{test_user_id}",
        gender=Gender.MALE,
        age_group=AgeGroup.TWENTIES,
        allergies=[],
        like_food_categories_id=["JAPANESE"],
        categories_id=["SUSHI"],
        other_characteristics="First time user",
    )

    request = UpdatePersonaDBRequest(
        user_data=user_data,
        review_data=[],  # 빈 리뷰 리스트
    )

    service = PersonaService()

    try:
        result = await service.create_and_save_persona(request)

        # 결과 검증
        assert result is not None
        assert result.id == test_user_id
        assert result.base_persona is not None
        assert len(result.base_persona) > 0

        print(f"\n[Integration Test - No Reviews] 생성된 페르소나:")
        print(f"User ID: {result.id}")
        print(f"Base Persona: {result.base_persona[:200]}...")

    except Exception as e:
        pytest.fail(f"Integration test with no reviews failed: {str(e)}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_persona_service_update_existing_persona():
    """
    기존 페르소나 업데이트 테스트
    """
    test_user_id = int(datetime.now().timestamp()) + 2000

    # 첫 번째 페르소나 생성
    user_data_v1 = UserData(
        id=test_user_id,
        nickname=f"update_test_user_{test_user_id}",
        gender=Gender.FEMALE,
        age_group=AgeGroup.TWENTIES,
        allergies=[],
        like_food_categories_id=["KOREAN"],
        categories_id=["KOREAN"],
        other_characteristics="Likes spicy food",
    )

    request_v1 = UpdatePersonaDBRequest(
        user_data=user_data_v1,
        review_data=[],
    )

    service = PersonaService()
    result_v1 = await service.create_and_save_persona(request_v1)

    print(f"\n[Integration Test - Update] 첫 번째 페르소나 생성:")
    print(f"Base Persona V1: {result_v1.base_persona[:100]}...")

    # 두 번째 페르소나 생성 (업데이트)
    user_data_v2 = UserData(
        id=test_user_id,  # 같은 ID
        nickname=f"update_test_user_{test_user_id}",
        gender=Gender.FEMALE,
        age_group=AgeGroup.TWENTIES,
        allergies=[AllergyType.PEACH],  # 알레르기 추가
        like_food_categories_id=["KOREAN", "JAPANESE"],  # 카테고리 추가
        categories_id=["KOREAN", "SUSHI"],
        other_characteristics="Likes spicy food and sushi",  # 특성 변경
    )

    review_data_v2 = [
        ReviewData(
            restaurant_id="test_rest_004",
            user_id=test_user_id,
            rating=5,
            comment="스시가 정말 신선하고 맛있어요!",
        ),
    ]

    request_v2 = UpdatePersonaDBRequest(
        user_data=user_data_v2,
        review_data=review_data_v2,
    )

    result_v2 = await service.create_and_save_persona(request_v2)

    print(f"[Integration Test - Update] 두 번째 페르소나 생성 (업데이트):")
    print(f"Base Persona V2: {result_v2.base_persona[:100]}...")

    # 검증
    assert result_v2.id == test_user_id
    assert AllergyType.PEACH in result_v2.allergies
    assert "JAPANESE" in result_v2.like_food_categories_id

    # DB에서 조회하여 최신 버전인지 확인
    from src.recommendation.features.persona_manager.repositories.persona_repository import (
        PersonaRepository,
    )

    repo = PersonaRepository()
    latest_persona = await repo.find_by_user_id(test_user_id)

    assert latest_persona is not None
    assert latest_persona.base_persona == result_v2.base_persona
    assert AllergyType.PEACH in latest_persona.allergies

    print(f"[Integration Test - Update] 업데이트 성공!")
