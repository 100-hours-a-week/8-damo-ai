import logging
from typing import Any, Dict, List

from shared.database.db_manager import DBManager
from services.iterative_discussion.app.engine.state import ConsensusState
from services.iterative_discussion.app.prompts.persona_templates import (
    PERSONA_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


def _build_persona_prompt(user: Dict[str, Any]) -> str:
    """유저의 basePersona와 알레르기 정보로 시스템 프롬프트 생성."""
    base_persona = user.get("basePersona") or user.get("base_persona") or ""
    allergies_raw = user.get("allergies", [])
    allergies = ", ".join(allergies_raw) if allergies_raw else "없음"

    return PERSONA_SYSTEM_PROMPT.format(
        nickname=user.get("nickname", "익명"),
        base_persona=base_persona or "정보 없음",
        allergies=allergies,
    )


async def persona_factory(state: ConsensusState) -> dict:
    """Node 1: user_ids로 DB에서 유저 데이터 조회 후 페르소나 프롬프트 생성."""
    user_ids = state.get("user_ids", [])
    if not user_ids:
        return {"is_error": True, "error_message": "user_ids가 비어있습니다."}

    db = DBManager(col_name="users")
    user_data_list: List[Dict[str, Any]] = []

    for uid in user_ids:
        try:
            doc = await db.read_one({"id": uid})
        except Exception:
            logger.warning("유저 DB 조회 실패: uid=%s", uid, exc_info=True)
            continue
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
