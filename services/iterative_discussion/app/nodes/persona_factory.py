import re
from typing import Any, Dict, List

from shared.database.db_manager import DBManager
from services.iterative_discussion.app.engine.state import ConsensusState
from services.iterative_discussion.app.prompts.persona_templates import (
    PERSONA_SYSTEM_PROMPT,
    SYSTEM_INSIGHT_HEADER,
)

INSIGHT_TAG_PATTERN = re.compile(r"\[System Insight]\s*(.+)")


def _extract_insights(other_characteristics: str) -> List[str]:
    """otherCharacteristics에서 [System Insight] 태그를 파싱."""
    return INSIGHT_TAG_PATTERN.findall(other_characteristics)


def _strip_insights(other_characteristics: str) -> str:
    """[System Insight] 태그를 제거한 원본 특이사항 반환."""
    return INSIGHT_TAG_PATTERN.sub("", other_characteristics).strip()


def _build_persona_prompt(user: Dict[str, Any]) -> str:
    """단일 유저 데이터로 시스템 프롬프트 생성."""
    other = user.get("other_characteristics") or user.get("otherCharacteristics") or ""

    insights = _extract_insights(other)
    clean_characteristics = _strip_insights(other) if insights else other

    system_insight_section = ""
    if insights:
        bullets = "\n".join(f"- {i}" for i in insights)
        system_insight_section = SYSTEM_INSIGHT_HEADER.format(insights=bullets)

    allergies_raw = user.get("allergies", [])
    allergies = ", ".join(allergies_raw) if allergies_raw else "없음"

    like_cats = user.get("like_food_categories_id") or user.get("likeFoodCategoriesId") or []
    categories = user.get("categories_id") or user.get("categoriesId") or []

    return PERSONA_SYSTEM_PROMPT.format(
        nickname=user.get("nickname", "익명"),
        gender=user.get("gender", "미지정"),
        age_group=user.get("age_group") or user.get("ageGroup") or "미지정",
        allergies=allergies,
        like_categories=", ".join(like_cats) if like_cats else "없음",
        categories=", ".join(categories) if categories else "없음",
        other_characteristics=clean_characteristics or "없음",
        system_insight_section=system_insight_section,
    )


async def persona_factory(state: ConsensusState) -> dict:
    """Node 1: user_ids로 DB에서 유저 데이터 조회 후 페르소나 프롬프트 생성."""
    user_ids = state.get("user_ids", [])
    if not user_ids:
        return {"is_error": True, "error_message": "user_ids가 비어있습니다."}

    db = DBManager(col_name="users")
    user_data_list: List[Dict[str, Any]] = []

    for uid in user_ids:
        doc = await db.read_one({"id": uid})
        if doc:
            doc.pop("_id", None)
            user_data_list.append(doc)

    if not user_data_list:
        return {"is_error": True, "error_message": "DB에서 유저 데이터를 찾을 수 없습니다."}

    persona_prompts: Dict[str, str] = {}
    for user in user_data_list:
        user_id = str(user.get("id", ""))
        if not user_id:
            continue
        persona_prompts[user_id] = _build_persona_prompt(user)

    return {
        "user_data_list": user_data_list,
        "persona_prompts": persona_prompts,
    }
