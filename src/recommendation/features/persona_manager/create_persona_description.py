from langchain_core.output_parsers import StrOutputParser
from src.shared.llm.llm_client import get_llm
from src.recommendation.features.persona_manager.prompts.persona_prompt import (
    BASE_PERSONA_PROMPT,
)
from src.recommendation.schemas.update_persona_db_request import UpdatePersonaDBRequest


async def create_persona_description(request: UpdatePersonaDBRequest) -> str:
    """
    UpdatePersonaDBRequest 데이터를 받아 LLM을 통해 페르소나 설명(문자열)을 생성
    """
    user_data = request.user_data

    # 1. 리뷰 데이터 포맷팅
    # 리뷰가 있으면 문자열로 변환하고, 없으면 "없음" 처리
    if request.review_data:
        reviews_str = "\n".join(
            [
                f"- {r.restaurant_id} | {r.rating}점 | {r.comment}"
                for r in request.review_data
            ]
        )
    else:
        reviews_str = "없음"

    # 2. 리스트 데이터 포맷팅
    allergies_str = ", ".join(user_data.allergies) if user_data.allergies else "없음"
    like_foods_str = ", ".join(user_data.like_foods) if user_data.like_foods else "없음"
    # preferred_ingredients는 UserData 모델에 없다면 적절한 필드로 매핑하거나 비워둡니다 (현재 스키마 기준).
    # 여기서는 like_ingredients를 활용하거나 임시로 같은 값을 사용하겠습니다.
    preferred_ingredients_str = (
        ", ".join(user_data.like_ingredients) if user_data.like_ingredients else "없음"
    )

    # 3. LLM 체인 구성 및 실행
    llm = get_llm(temperature=0.7)  # 창의성 조절
    chain = BASE_PERSONA_PROMPT | llm | StrOutputParser()

    persona_desc = await chain.ainvoke(
        {
            "nickname": user_data.nickname,
            "gender": user_data.gender,
            "age_group": user_data.age_group,
            "allergies": allergies_str,
            "like_food_categories": like_foods_str,
            "preferred_ingredients": preferred_ingredients_str,
            "other_characteristics": user_data.other_characteristics,
            "reviews": reviews_str,
        }
    )

    return persona_desc.strip('"')  # 혹시 모를 따옴표 제거
