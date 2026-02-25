import logging
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage

from shared.database.db_manager import DBManager
from services.iterative_discussion.app.engine.llm_factory import get_chat_llm
from services.iterative_discussion.app.engine.state import ConsensusState

logger = logging.getLogger(__name__)

EVOLUTION_PROMPT = """\
당신은 식당 추천 시스템의 페르소나 분석가입니다.

아래는 이전 추천에서 페르소나가 예측한 투표와 유저의 실제 반응입니다.

## 페르소나 예측
{persona_prediction}

## 실제 유저 반응
{actual_reaction}

예측과 실제 반응이 불일치하는 부분을 분석하고,
다음 추천에서 페르소나를 보정하기 위한 인사이트를 1~2문장으로 작성하세요.

응답 형식: 인사이트 내용만 작성 (태그, JSON 없이 순수 텍스트)
"""


async def _fetch_previous_votes(dining_id: int) -> List[Dict[str, Any]]:
    """이전 추천의 persona_votes를 DB에서 조회."""
    db = DBManager(col_name="dining_sessions")
    session = await db.read_one({"diningId": dining_id})
    if not session:
        return []

    phases = session.get("phases", [])
    if not phases:
        return []

    # 가장 최근 phase의 persona_votes
    latest = phases[-1] if isinstance(phases, list) else {}
    return latest.get("persona_votes", [])


def _find_mismatches(
    previous_votes: List[Dict[str, Any]],
    vote_result_list: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """페르소나 예측 vs 실제 반응 불일치를 찾는다.

    Returns:
        [{"user_id": ..., "restaurant_id": ..., "predicted": True, "actual": "dislike"}, ...]
    """
    # 실제 반응 매핑: restaurant_id → {liked_user_ids, disliked_user_ids}
    actual_map: Dict[str, Dict[str, List[int]]] = {}
    for vr in vote_result_list:
        rid = vr.get("restaurant_id") or vr.get("restaurantId") or ""
        actual_map[rid] = {
            "liked": vr.get("liked_user_ids") or vr.get("likedUserIds") or [],
            "disliked": vr.get("disliked_user_ids") or vr.get("dislikedUserIds") or [],
        }

    mismatches = []
    for vote_entry in previous_votes:
        user_id = vote_entry.get("user_id", "")
        uid_int = int(user_id) if user_id else 0

        for vote in vote_entry.get("votes", []):
            rid = vote.get("restaurant_id", "")
            predicted_approve = vote.get("approve", True)
            actual = actual_map.get(rid, {})

            # 실제 반응 판단
            if uid_int in actual.get("liked", []):
                actual_approve = True
            elif uid_int in actual.get("disliked", []):
                actual_approve = False
            else:
                continue  # 투표 안 한 식당은 스킵

            if predicted_approve != actual_approve:
                mismatches.append({
                    "user_id": user_id,
                    "restaurant_id": rid,
                    "predicted": predicted_approve,
                    "actual": "like" if actual_approve else "dislike",
                    "reasoning": vote.get("reasoning", ""),
                })

    return mismatches


async def self_evolution(state: ConsensusState) -> dict:
    """재추천 시 페르소나 예측 vs 실제 반응을 비교하여 페르소나 프롬프트를 보정."""
    try:
        vote_result_list = state.get("vote_result_list", [])
        dining_data = state.get("dining_data", {})
        persona_prompts = dict(state.get("persona_prompts", {}))

        dining_id = dining_data.get("diningId") or dining_data.get("dining_id")
        if not dining_id:
            return {}  # dining_id 없으면 진화 스킵

        # 이전 페르소나 투표 조회
        previous_votes = await _fetch_previous_votes(dining_id)
        if not previous_votes:
            return {}  # 이전 투표 없으면 진화 스킵

        # 불일치 찾기
        mismatches = _find_mismatches(previous_votes, vote_result_list)
        if not mismatches:
            return {}  # 전부 일치하면 보정 불필요

        # 유저별 불일치 그룹핑
        user_mismatches: Dict[str, List[Dict[str, Any]]] = {}
        for m in mismatches:
            uid = m["user_id"]
            user_mismatches.setdefault(uid, []).append(m)

        llm = get_chat_llm(temperature=0.3)
        db = DBManager(col_name="users")

        for user_id, user_misses in user_mismatches.items():
            # LLM으로 인사이트 생성
            prediction_text = "\n".join(
                f"- {m['restaurant_id']}: {'찬성' if m['predicted'] else '반대'} (사유: {m['reasoning']})"
                for m in user_misses
            )
            actual_text = "\n".join(
                f"- {m['restaurant_id']}: 실제 반응 {m['actual']}"
                for m in user_misses
            )

            prompt = EVOLUTION_PROMPT.format(
                persona_prediction=prediction_text,
                actual_reaction=actual_text,
            )

            response = await llm.ainvoke([HumanMessage(content=prompt)])
            insight = response.content.strip()

            if not insight:
                continue

            # 페르소나 프롬프트에 인사이트 삽입
            if user_id in persona_prompts:
                insight_line = f"\n[System Insight] {insight}"
                persona_prompts[user_id] = insight_line + "\n" + persona_prompts[user_id]

            # DB의 otherCharacteristics에도 저장 (다음 세션에서 Node 1이 읽음)
            uid_int = int(user_id) if user_id else 0
            if uid_int:
                user_doc = await db.read_one({"id": uid_int})
                if user_doc:
                    existing = user_doc.get("otherCharacteristics") or user_doc.get("other_characteristics") or ""
                    updated = existing + f"\n[System Insight] {insight}"
                    await db.update_one({"id": uid_int}, {"otherCharacteristics": updated})

        return {"persona_prompts": persona_prompts}
    except Exception:
        logger.warning("self_evolution 실패, 보정 스킵", exc_info=True)
        return {}
