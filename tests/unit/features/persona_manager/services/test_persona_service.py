import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.recommendation.features.persona_manager.services.persona_service import (
    PersonaService,
)
from src.recommendation.schemas.update_persona_db_request import UpdatePersonaDBRequest
from src.recommendation.schemas.user_data import UserData
from src.recommendation.schemas.review_data import ReviewData
from src.recommendation.features.persona_manager.entities.persona import PersonaDocument
from src.recommendation.entities.restaurant import RestaurantDocument
from src.recommendation.enums import Gender, AgeGroup, AllergyType


@pytest.fixture
def mock_user_data():
    """테스트용 사용자 데이터"""
    return UserData(
        id=1,
        nickname="test_user",
        gender=Gender.MALE,
        age_group=AgeGroup.TWENTIES,
        allergies=[AllergyType.PEACH],
        like_food_categories_id=["KOREAN", "JAPANESE"],
        categories_id=["KOREAN", "JAPANESE"],
        other_characteristics="Likes quiet atmosphere",
    )


@pytest.fixture
def mock_review_data():
    """테스트용 리뷰 데이터"""
    return [
        ReviewData(
            restaurant_id="rest_001",
            user_id=1,
            rating=5,
            comment="음식이 정말 맛있어요!",
        ),
        ReviewData(
            restaurant_id="rest_002",
            user_id=1,
            rating=4,
            comment="분위기가 좋았습니다",
        ),
    ]


@pytest.fixture
def mock_restaurants():
    """테스트용 식당 데이터"""
    return [
        RestaurantDocument(
            id="rest_001",
            place_name="청담동 스시오마카세",
            address_name="서울 강남구 청담동",
            road_address_name="서울 강남구 청담대로 123",
            category_group_name="음식점",
            category_detail="일식",
            phone="02-1234-5678",
            place_url="http://example.com",
            x="127.0",
            y="37.5",
        ),
        RestaurantDocument(
            id="rest_002",
            place_name="강남 이탈리안 레스토랑",
            address_name="서울 강남구 역삼동",
            road_address_name="서울 강남구 테헤란로 456",
            category_group_name="음식점",
            category_detail="이탈리아음식",
            phone="02-9876-5432",
            place_url="http://example.com",
            x="127.1",
            y="37.6",
        ),
    ]


@pytest.fixture
def mock_request(mock_user_data, mock_review_data):
    """테스트용 요청 데이터"""
    return UpdatePersonaDBRequest(
        user_data=mock_user_data,
        review_data=mock_review_data,
    )


class TestPersonaService:
    """PersonaService Unit Tests"""

    @pytest.mark.asyncio
    async def test_create_and_save_persona_success(
        self, mock_request, mock_restaurants
    ):
        """페르소나 생성 및 저장 성공 테스트"""
        service = PersonaService()

        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.content = (
            "사용자는 일식과 이탈리아 음식을 선호하며, 조용한 분위기를 좋아합니다."
        )

        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_llm_response)

        # Mock repositories
        with (
            patch.object(
                service.restaurant_repo, "find_by_ids", return_value=mock_restaurants
            ) as mock_find_restaurants,
            patch.object(service.persona_repo, "save") as mock_save,
            patch(
                "src.recommendation.features.persona_manager.services.persona_service.get_llm"
            ) as mock_get_llm,
            patch(
                "src.recommendation.features.persona_manager.services.persona_service.BASE_PERSONA_PROMPT"
            ) as mock_prompt,
        ):
            # Setup mocks
            mock_get_llm.return_value = MagicMock()
            mock_prompt.__or__.return_value = mock_chain

            mock_saved_doc = PersonaDocument(
                id=1,
                nickname="test_user",
                gender=Gender.MALE,
                age_group=AgeGroup.TWENTIES,
                allergies=[AllergyType.PEACH],
                like_food_categories_id=["KOREAN", "JAPANESE"],
                categories_id=["KOREAN", "JAPANESE"],
                other_characteristics="Likes quiet atmosphere",
                base_persona=mock_llm_response.content,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            mock_save.return_value = mock_saved_doc

            # Execute
            result = await service.create_and_save_persona(mock_request)

            # Assertions
            assert result.id == 1
            assert result.nickname == "test_user"
            assert result.base_persona == mock_llm_response.content

            # Verify restaurant lookup was called
            mock_find_restaurants.assert_called_once()
            called_ids = mock_find_restaurants.call_args[0][0]
            assert "rest_001" in called_ids
            assert "rest_002" in called_ids

            # Verify LLM chain was invoked
            mock_chain.ainvoke.assert_called_once()

            # Verify save was called
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_format_reviews_with_restaurant_info(
        self, mock_review_data, mock_restaurants
    ):
        """식당 정보 포함 리뷰 포맷팅 테스트"""
        service = PersonaService()

        with patch.object(
            service.restaurant_repo, "find_by_ids", return_value=mock_restaurants
        ):
            result = await service._format_reviews_with_restaurant_info(
                mock_review_data
            )

            # 식당 정보가 포함되어야 함
            assert "청담동 스시오마카세" in result
            assert "일식" in result
            assert "강남 이탈리안 레스토랑" in result
            assert "이탈리아음식" in result

            # 리뷰 내용이 포함되어야 함
            assert "음식이 정말 맛있어요!" in result
            assert "분위기가 좋았습니다" in result

            # 평점이 포함되어야 함
            assert "5점" in result
            assert "4점" in result

    @pytest.mark.asyncio
    async def test_format_reviews_with_missing_restaurant(self, mock_review_data):
        """식당 정보를 찾지 못한 경우 리뷰 포맷팅 테스트"""
        service = PersonaService()

        # 빈 식당 리스트 반환 (식당 정보를 찾지 못함)
        with patch.object(service.restaurant_repo, "find_by_ids", return_value=[]):
            result = await service._format_reviews_with_restaurant_info(
                mock_review_data
            )

            # 기본 형식으로 포맷팅되어야 함
            assert "5점: 음식이 정말 맛있어요!" in result
            assert "4점: 분위기가 좋았습니다" in result

    @pytest.mark.asyncio
    async def test_format_reviews_empty_list(self):
        """빈 리뷰 리스트 처리 테스트"""
        service = PersonaService()

        result = await service._format_reviews_with_restaurant_info([])

        assert result == "작성한 리뷰 없음"

    @pytest.mark.asyncio
    async def test_format_reviews_max_5_reviews(self, mock_restaurants):
        """최대 5개 리뷰만 처리하는지 테스트"""
        service = PersonaService()

        # 10개의 리뷰 생성
        many_reviews = [
            ReviewData(
                restaurant_id=f"rest_{i:03d}",
                user_id=1,
                rating=5,
                comment=f"리뷰 {i}",
            )
            for i in range(10)
        ]

        with patch.object(
            service.restaurant_repo, "find_by_ids", return_value=mock_restaurants
        ) as mock_find:
            await service._format_reviews_with_restaurant_info(many_reviews)

            # find_by_ids가 최대 5개의 ID로만 호출되어야 함
            called_ids = mock_find.call_args[0][0]
            assert len(called_ids) == 5

    def test_create_persona_document(self, mock_user_data):
        """PersonaDocument 생성 테스트"""
        service = PersonaService()
        persona_text = "테스트 페르소나"

        result = service._create_persona_document(mock_user_data, persona_text)

        assert result.id == 1
        assert result.nickname == "test_user"
        assert result.gender == Gender.MALE
        assert result.age_group == AgeGroup.TWENTIES
        assert result.base_persona == persona_text
        assert AllergyType.PEACH in result.allergies
        assert "KOREAN" in result.like_food_categories_id
        assert isinstance(result.created_at, datetime)
        assert isinstance(result.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_generate_persona_calls_llm_with_correct_params(
        self, mock_user_data, mock_review_data, mock_restaurants
    ):
        """LLM 호출 시 올바른 파라미터가 전달되는지 테스트"""
        service = PersonaService()

        mock_llm_response = MagicMock()
        mock_llm_response.content = "Generated persona"

        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_llm_response)

        with (
            patch.object(
                service.restaurant_repo, "find_by_ids", return_value=mock_restaurants
            ),
            patch(
                "src.recommendation.features.persona_manager.services.persona_service.get_llm"
            ) as mock_get_llm,
            patch(
                "src.recommendation.features.persona_manager.services.persona_service.BASE_PERSONA_PROMPT"
            ) as mock_prompt,
        ):
            mock_get_llm.return_value = MagicMock()
            mock_prompt.__or__.return_value = mock_chain

            result = await service._generate_persona(mock_user_data, mock_review_data)

            # LLM 호출 확인
            mock_chain.ainvoke.assert_called_once()

            # 전달된 파라미터 확인
            call_args = mock_chain.ainvoke.call_args[0][0]
            assert call_args["nickname"] == "test_user"
            assert call_args["gender"] == Gender.MALE
            assert call_args["age_group"] == AgeGroup.TWENTIES
            assert "KOREAN" in call_args["like_food_categories"]
            assert "KOREAN" in call_args["preferred_ingredients"]
            assert call_args["other_characteristics"] == "Likes quiet atmosphere"

            # 리뷰 텍스트에 식당 정보가 포함되어 있는지 확인
            assert "청담동 스시오마카세" in call_args["reviews"]
            assert "일식" in call_args["reviews"]

            assert result == "Generated persona"
