from src.shared.llm.llm_client import get_llm
from src.recommendation.features.persona_manager.workflows.state import PersonaState
from src.recommendation.features.persona_manager.repositories.persona_repository import (
    PersonaRepository,
)
from src.recommendation.features.persona_manager.entities.persona import PersonaDocument
from src.recommendation.features.persona_manager.prompts.persona_prompt import (
    BASE_PERSONA_PROMPT,
)
from datetime import datetime


async def generate_base_persona_node(state: PersonaState) -> PersonaState:
    """
    사용자 데이터를 바탕으로 LLM을 사용해 페르소나(base_persona)를 생성하는 노드
    """
    request_data = state["request_data"]
    user = request_data.user_data
    reviews = request_data.review_data

    # 프롬프트 템플릿 로드
    prompt = BASE_PERSONA_PROMPT

    # 리뷰 데이터 텍스트 변환
    reviews_text = ""
    if reviews:
        reviews_text = "\n".join(
            [f"- {r.rating}점: {r.comment}" for r in reviews[:5]]
        )  # 최대 5개만 활용
    else:
        reviews_text = "작성한 리뷰 없음"

    # LLM 호출
    llm = get_llm()
    chain = prompt | llm

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

    return {"generated_base_persona": response.content}


async def save_persona_node(state: PersonaState) -> PersonaState:
    """
    생성된 페르소나와 사용자 정보를 DB에 저장하는 노드
    """
    request_data = state["request_data"]
    base_persona = state["generated_base_persona"]
    user = request_data.user_data

    repo = PersonaRepository()

    # PersonaDocument 생성
    document = PersonaDocument(
        id=user.id,
        nickname=user.nickname,
        gender=user.gender,
        age_group=user.age_group,
        allergies=user.allergies,
        like_food_categories_id=user.like_food_categories_id,
        categories_id=user.categories_id,
        other_characteristics=user.other_characteristics,
        base_persona=base_persona,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # DB 저장
    saved_doc = await repo.save(document)

    return {"final_document": saved_doc}
