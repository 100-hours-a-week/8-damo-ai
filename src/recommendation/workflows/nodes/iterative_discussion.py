import logging
from typing import List

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.recommendation.entities.persona import Persona
from src.recommendation.repositories.persona_repository import PersonaRepository
from src.recommendation.workflows.states.recommendation_state import RecommendationState
from src.shared.llm.llm_client import get_llm

# Initialize logger
logger = logging.getLogger(__name__)


# Output schema for structured generation
class RecommendationItem(BaseModel):
    restaurant_id: str = Field(description="The ID of the restaurant")
    place_name: str = Field(description="The name of the restaurant")
    reasoning_description: str = Field(
        description="Reasoning for why this restaurant was selected for the group"
    )


class RecommendationResult(BaseModel):
    items: List[RecommendationItem] = Field(
        description="List of recommended restaurants, ranked by preference"
    )


async def iterative_discussion_node(state: RecommendationState) -> dict:
    """
    Personas and filtered restaurants are analyzed to provide a ranked recommendation.
    """
    user_ids = state["user_ids"]
    filtered_restaurants = state["filtered_restaurants"]

    # 1. Fetch Personas
    persona_repo = PersonaRepository()
    personas: List[Persona] = []

    for uid in user_ids:
        # Assuming user_ids are integers matching Persona IDs
        p = await persona_repo.find_by_id(uid)
        if p:
            personas.append(p)
        else:
            logger.warning(f"Persona not found for user_id: {uid}")

    if not personas:
        logger.error("No personas found for the given user IDs.")
        # Continue with empty personas or handle error.
        # For now, proceeding creates a generic recommendation but logs the issue.

    # Convert personas to dict for prompt
    personas_data = [p.model_dump() for p in personas]

    # Simplify restaurant data for LLM context window efficiency
    restaurants_context = []
    for r in filtered_restaurants:
        # Ensure we handle dictionary access safely
        restaurants_context.append(
            {
                "id": r.get("id") or r.get("_id"),
                "place_name": r.get("place_name"),
                "category": r.get("category_detail") or r.get("category_group_name"),
                "menus": r.get("menus", [])[:5],  # Limit menus to save tokens
                "business_hour": r.get("business_hour"),
            }
        )

    # 2. Call Gemini API
    # Using a slightly lower temperature for consistent ranking
    llm = get_llm(temperature=0.2)

    parser = JsonOutputParser(pydantic_object=RecommendationResult)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "당신은 그룹 의사결정을 조율하는 전문 다이닝 컨설턴트입니다. 그룹 멤버들의 페르소나와 후보 식당 리스트를 참고할 수 있습니다.",
            ),
            (
                "user",
                """
        다음 페르소나와 후보 식당 정보를 바탕으로, 이 그룹에게 가장 적합한 식당부터 순서대로 리스트를 정렬해 주세요.
        
        고려사항:
        1. 각 페르소나의 식습관과 취향
        2. 그룹 내 역학 관계 (예: 특정 멤버가 싫어하는 음식 피하기)
        3. 그룹에 어울리는 전반적인 분위기
        
        그룹 페르소나:
        {personas}
        
        후보 식당:
        {restaurants}
        
        결과는 JSON 형식으로 'restaurant_id', 'place_name', 'reasoning_description'(선정 이유)을 포함한 리스트로 출력해 주세요.
        
        {format_instructions}
        """,
            ),
        ]
    )

    chain = prompt | llm | parser

    try:
        result = await chain.ainvoke(
            {
                "personas": personas_data,
                "restaurants": restaurants_context,
                "format_instructions": parser.get_format_instructions(),
            }
        )

        # Re-order filtered_restaurants based on the LLM result
        ranked_items = result.get("items", [])

        # Create a map for quick access: ID -> Restaurant Object
        # Handling both 'id' and '_id' is crucial for MongoDB objects
        restaurant_map = {
            str(r.get("id") or r.get("_id")): r for r in filtered_restaurants
        }

        sorted_restaurants = []
        for item in ranked_items:
            rid = item.get("restaurant_id")
            if rid in restaurant_map:
                # Append the original restaurant object in the new order
                # We could attach the reasoning here if needed: restaurant_map[rid]['reasoning'] = item.get('reasoning_description')
                sorted_restaurants.append(restaurant_map[rid])

        # If any restaurants were missed by the LLM (truncation/error), optionally append them?
        # For now, we assume the LLM's returned list is the "filtered" and "sorted" selection.

        return {
            "filtered_restaurants": sorted_restaurants,
            "personas": [
                p.model_dump() for p in personas
            ],  # Update state with fetched available personas
            "status_message": [
                "Iterative discussion completed",
                f"Ranked {len(sorted_restaurants)} restaurants based on {len(personas)} personas.",
            ],
        }

    except Exception as e:
        logger.error(f"Error in iterative_discussion_node: {e}")
        return {
            "error_message": str(e),
            "status_message": ["Error during discussion phase"],
        }
