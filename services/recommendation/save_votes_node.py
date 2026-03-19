"""Save votes node: persona_votes를 MongoDB에 저장.

실패해도 파이프라인을 중단하지 않는다.
"""
import logging

from langfuse import observe

from shared.database.db_manager import DBManager
from services.recommendation.state import PipelineState

logger = logging.getLogger(__name__)


@observe(name="save_votes")
async def save_votes_node(state: PipelineState) -> dict:
    """persona_votes를 dining_sessions.phases에 push."""
    dining_id = state.get("dining_id")
    persona_votes = state.get("persona_votes", [])

    logger.info(
        "[SAVE_VOTES] 저장 시작: dining_id=%s, votes=%d건",
        dining_id,
        len(persona_votes),
    )

    try:
        db = DBManager(col_name="dining_sessions")
        await db.update_one_with_command(
            {"diningId": int(dining_id)},
            {"$push": {"phases": {"persona_votes": persona_votes}}},
            upsert=True,
        )
        logger.info("[SAVE_VOTES] 저장 완료: dining_id=%s", dining_id)
    except Exception:
        logger.warning(
            "[SAVE_VOTES] 저장 실패 (파이프라인 계속): dining_id=%s",
            dining_id,
            exc_info=True,
        )

    return {}
