from typing import List
from datetime import datetime

from src.shared.llm.llm_client import get_llm
from src.recommendation.schemas.update_persona_db_request import UpdatePersonaDBRequest
from src.recommendation.schemas.user_data import UserData
from src.recommendation.schemas.review_data import ReviewData
from src.recommendation.features.persona_manager.entities.persona import PersonaDocument
from src.recommendation.features.persona_manager.repositories.persona_repository import (
    PersonaRepository,
)
from src.recommendation.features.persona_manager.repositories.restaurant_repository import (
    RestaurantRepository,
)
from src.recommendation.features.persona_manager.prompts.persona_prompt import (
    BASE_PERSONA_PROMPT,
)


class PersonaService:
    """
    페르소나 생성 및 관리를 담당하는 서비스 레이어
    LangChain을 사용하여 LLM 기반 페르소나 생성
    """

    def __init__(self):
        self.persona_repo = PersonaRepository()
        self.restaurant_repo = RestaurantRepository()

    async def create_and_save_persona(
        self, request: UpdatePersonaDBRequest
    ) -> PersonaDocument:
        """
        사용자 데이터와 리뷰를 기반으로 페르소나를 생성하고 DB에 저장합니다.

        Args:
            request: 사용자 데이터 및 리뷰 데이터

        Returns:
            저장된 PersonaDocument
        """
        # 1. 페르소나 생성
        persona_text = await self._generate_persona(
            request.user_data, request.review_data
        )

        # 2. PersonaDocument 생성
        document = self._create_persona_document(request.user_data, persona_text)

        # 3. DB 저장
        saved_document = await self.persona_repo.save(document)

        return saved_document

    async def _generate_persona(self, user: UserData, reviews: List[ReviewData]) -> str:
        """
        LangChain을 사용하여 사용자 페르소나를 생성합니다.

        Args:
            user: 사용자 정보
            reviews: 리뷰 데이터 리스트

        Returns:
            생성된 페르소나 텍스트
        """
        # 리뷰 텍스트 생성 (식당 정보 포함)
        reviews_text = await self._format_reviews_with_restaurant_info(reviews)

        # LangChain으로 LLM 호출
        llm = get_llm()
        chain = BASE_PERSONA_PROMPT | llm

        response = await chain.ainvoke(
            {
                "nickname": user.nickname,
                "gender": user.gender,
                "age_group": user.age_group,
                "allergies": ", ".join([a.value for a in user.allergies]),
                "like_food_categories": ", ".join(user.like_food_categories_id),
                "preferred_ingredients": ", ".join(user.categories_id),
                "other_characteristics": user.other_characteristics,
                "reviews": reviews_text,
            }
        )

        return response.content

    async def _format_reviews_with_restaurant_info(
        self, reviews: List[ReviewData]
    ) -> str:
        """
        리뷰 데이터를 식당 정보와 함께 포맷팅합니다.

        Args:
            reviews: 리뷰 데이터 리스트

        Returns:
            포맷팅된 리뷰 텍스트
        """
        if not reviews:
            return "작성한 리뷰 없음"

        # 최대 5개 리뷰만 사용
        top_reviews = reviews[:5]

        # Restaurant 정보 일괄 조회
        restaurant_ids = [r.restaurant_id for r in top_reviews]
        restaurants = await self.restaurant_repo.find_by_ids(restaurant_ids)

        # restaurant_id를 키로 하는 딕셔너리 생성
        restaurant_map = {r.id: r for r in restaurants if r.id}

        # 리뷰 텍스트 생성 (식당 정보 포함)
        review_lines = []
        for review in top_reviews:
            restaurant = restaurant_map.get(review.restaurant_id)
            if restaurant:
                review_lines.append(
                    f"- [{restaurant.place_name}({restaurant.category_detail})] "
                    f"{review.rating}점: {review.comment}"
                )
            else:
                # 식당 정보를 찾지 못한 경우 기본 형식
                review_lines.append(f"- {review.rating}점: {review.comment}")

        return "\n".join(review_lines)

    def _create_persona_document(
        self, user: UserData, persona_text: str
    ) -> PersonaDocument:
        """
        PersonaDocument 엔티티를 생성합니다.

        Args:
            user: 사용자 정보
            persona_text: 생성된 페르소나 텍스트

        Returns:
            PersonaDocument
        """
        return PersonaDocument(
            id=user.id,
            nickname=user.nickname,
            gender=user.gender,
            age_group=user.age_group,
            allergies=user.allergies,
            like_food_categories_id=user.like_food_categories_id,
            categories_id=user.categories_id,
            other_characteristics=user.other_characteristics,
            base_persona=persona_text,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
