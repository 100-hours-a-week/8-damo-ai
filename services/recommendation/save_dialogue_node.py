"""Save dialogue node: 페르소나 간 대화 기록을 MongoDB에 저장.

dialogue_history를 dining_sessions에 저장해 향후 추천 이유 생성 등에 활용한다.
실패해도 파이프라인을 중단하지 않는다.
"""
import logging

from langfuse import observe

from shared.database.db_manager import DBManager
from services.recommendation.state import PipelineState

logger = logging.getLogger(__name__)


@observe(name="save_dialogue")
async def save_dialogue_node(state: PipelineState) -> dict:
    """dialogue_history를 dining_sessions.dialogueHistory에 저장."""
    dining_id = state.get("dining_id")
    dialogue_history = state.get("dialogue_history", [])

    logger.info(
        "[SAVE_DIALOGUE] 저장 시작: dining_id=%s, entries=%d건",
        dining_id,
        len(dialogue_history),
    )

    try:
        db = DBManager(col_name="dining_sessions")
        await db.update_one_with_command(
            {"diningId": int(dining_id)},
            {"$set": {"dialogueHistory": dialogue_history}},
            upsert=True,
        )
        logger.info("[SAVE_DIALOGUE] 저장 완료: dining_id=%s", dining_id)
    except Exception:
        logger.warning(
            "[SAVE_DIALOGUE] 저장 실패 (파이프라인 계속): dining_id=%s",
            dining_id,
            exc_info=True,
        )

    return {}
