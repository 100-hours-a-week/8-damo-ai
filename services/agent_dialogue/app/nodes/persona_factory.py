import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from langfuse import observe

from shared.database.db_manager import DBManager
from services.agent_dialogue.app.engine.state import AgentDialogueState
from services.agent_dialogue.app.prompts.langfuse_prompts import get_prompt
from services.agent_dialogue.app.prompts.persona_templates import PERSONA_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_FEEDBACK_MARKER = "## 이전 추천 피드백\n"
_FEEDBACK_FOOTER = "위 피드백을 참고하여, 이번 대화에서는 유저의 실제 취향에 더 가까운 의견을 내세요."


# ── self_evolution 로직 ────────────────────────────────────────────────────


@dataclass(frozen=True)
class VoteComparison:
    """페르소나 예측 vs 실제 투표 비교 결과 한 건."""

    restaurant_id: str
    place_name: str
    predicted_approve: bool
    actual_approve: bool
    reasoning: str
    is_correct: bool = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "is_correct", self.predicted_approve == self.actual_approve
        )


async def _fetch_previous_votes(dining_id: int) -> List[Dict[str, Any]]:
    """이전 추천의 persona_votes를 DB에서 조회.

    agent_dialogue는 flat 포맷으로 저장:
    [{user_id, restaurant_id, nickname, approve, reasoning}, ...]
    """
    db = DBManager(col_name="dining_sessions")
    session = await db.read_one({"diningId": dining_id})
    if not session:
        return []

    phases = session.get("phases", [])
    if not phases:
        return []

    latest = phases[-1] if isinstance(phases, list) else {}
    return latest.get("persona_votes", [])


def _build_actual_map(
    vote_result_list: List[Dict[str, Any]],
) -> Dict[str, Dict[str, List[int]]]:
    """실제 투표 결과를 restaurant_id 기준 매핑으로 변환."""
    actual_map: Dict[str, Dict[str, List[int]]] = {}
    for vr in vote_result_list:
        rid = str(vr.get("restaurant_id") or vr.get("restaurantId") or "")
        actual_map[rid] = {
            "liked": vr.get("liked_user_ids") or vr.get("likedUserIds") or [],
            "disliked": vr.get("disliked_user_ids") or vr.get("dislikedUserIds") or [],
        }
    return actual_map


def _compare_votes(
    user_id: str,
    previous_votes: List[Dict[str, Any]],
    actual_map: Dict[str, Dict[str, List[int]]],
) -> Tuple[List[VoteComparison], List[VoteComparison]]:
    """유저 한 명의 페르소나 예측 vs 실제 투표 비교 (flat 포맷).

    Returns:
        (correct_list, incorrect_list) 튜플
    """
    try:
        uid_int = int(user_id) if user_id else 0
    except (ValueError, TypeError):
        return [], []

    correct: List[VoteComparison] = []
    incorrect: List[VoteComparison] = []

    # flat 포맷: [{user_id, restaurant_id, approve, reasoning, place_name?}, ...]
    user_votes = [v for v in previous_votes if str(v.get("user_id", "")) == user_id]

    for vote in user_votes:
        rid = str(vote.get("restaurant_id", ""))
        actual = actual_map.get(rid)
        if not actual:
            continue

        predicted_approve = vote.get("approve", True)

        if uid_int in actual.get("liked", []):
            actual_approve = True
        elif uid_int in actual.get("disliked", []):
            actual_approve = False
        else:
            continue

        comparison = VoteComparison(
            restaurant_id=rid,
            place_name=vote.get("place_name", rid),
            predicted_approve=predicted_approve,
            actual_approve=actual_approve,
            reasoning=vote.get("reasoning", ""),
        )

        if comparison.is_correct:
            correct.append(comparison)
        else:
            incorrect.append(comparison)

    return correct, incorrect


def _format_vote_feedback(
    correct: List[VoteComparison],
    incorrect: List[VoteComparison],
) -> str:
    """맞춘/틀린 케이스를 few-shot 텍스트로 포맷."""
    if not correct and not incorrect:
        return ""

    lines: List[str] = []

    if correct:
        lines.append("[맞춘 케이스]")
        for c in correct:
            pred = "찬성" if c.predicted_approve else "반대"
            actual = "좋아요" if c.actual_approve else "싫어요"
            lines.append(
                f"- {c.place_name}: {pred} → 유저도 {actual} \u2713 (사유: {c.reasoning})"
            )

    if incorrect:
        lines.append("[틀린 케이스]")
        for c in incorrect:
            pred = "찬성" if c.predicted_approve else "반대"
            actual = "좋아요" if c.actual_approve else "싫어요"
            lines.append(
                f"- {c.place_name}: {pred} → 유저는 {actual} \u2717 (사유: {c.reasoning})"
            )

    lines.append("")
    lines.append(_FEEDBACK_FOOTER)
    return "\n".join(lines)


async def _apply_self_evolution(
    dining_id: int,
    vote_result_list: List[Dict[str, Any]],
    persona_prompts: Dict[str, str],
) -> Dict[str, str]:
    """재추천 시 이전 가상투표 vs 실제 투표 비교 → 프롬프트에 few-shot 피드백 주입."""
    try:
        previous_votes = await _fetch_previous_votes(dining_id)
        if not previous_votes:
            return persona_prompts

        actual_map = _build_actual_map(vote_result_list)
        updated = dict(persona_prompts)

        for user_id in updated:
            correct, incorrect = _compare_votes(user_id, previous_votes, actual_map)
            feedback_text = _format_vote_feedback(correct, incorrect)

            if not feedback_text:
                continue

            prompt = updated[user_id]
            if _FEEDBACK_MARKER not in prompt:
                logger.warning(
                    "self_evolution: feedback marker not found for user=%s", user_id
                )
                continue

            updated[user_id] = prompt.replace(
                _FEEDBACK_MARKER,
                f"{_FEEDBACK_MARKER}{feedback_text}\n",
                1,
            )
            logger.info(
                "self_evolution: user=%s correct=%d incorrect=%d",
                user_id,
                len(correct),
                len(incorrect),
            )

        return updated
    except Exception:
        logger.warning("self_evolution 실패, 보정 스킵", exc_info=True)
        return persona_prompts


# ── persona_factory 노드 ───────────────────────────────────────────────────


def _build_persona_prompt(user: Dict[str, Any]) -> str:
    """유저의 basePersona와 알레르기 정보로 시스템 프롬프트 생성."""
    base_persona = user.get("basePersona") or user.get("base_persona") or ""
    allergies_raw = user.get("allergies", [])
    allergies = ", ".join(allergies_raw) if allergies_raw else "없음"

    text, _ = get_prompt(
        "persona-system-prompt",
        PERSONA_SYSTEM_PROMPT,
        nickname=user.get("nickname", "익명"),
        base_persona=base_persona or "정보 없음",
        allergies=allergies,
        vote_feedback="",
    )
    return text


@observe(name="persona_factory")
async def persona_factory(state: AgentDialogueState) -> dict:
    """Node 1: user_ids로 DB에서 유저 데이터 조회 후 페르소나 프롬프트 생성.
    재추천 시 self_evolution 로직을 통합 실행하여 few-shot 피드백을 주입한다.
    """
    user_ids = state.get("user_ids", [])
    logger.info("[Node1] persona_factory 시작: user_ids=%s", user_ids)

    if not user_ids:
        logger.warning("[Node1] user_ids가 비어있어 에러 반환")
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
        logger.warning("[Node1] DB에서 유저 데이터를 찾을 수 없음")
        return {"is_error": True, "error_message": "DB에서 유저 데이터를 찾을 수 없습니다."}

    persona_prompts: Dict[str, str] = {}
    for user in user_data_list:
        user_id = str(user.get("id", ""))
        if not user_id:
            continue
        persona_prompts[user_id] = _build_persona_prompt(user)

    # self_evolution: 재추천 시 few-shot 피드백 주입
    vote_result_list = state.get("vote_result_list", [])
    if vote_result_list:
        dining_data = state.get("dining_data", {})
        dining_id = dining_data.get("diningId") or dining_data.get("dining_id")
        if dining_id:
            logger.info("[Node1] self_evolution 실행: dining_id=%s", dining_id)
            persona_prompts = await _apply_self_evolution(
                dining_id, vote_result_list, persona_prompts
            )

    logger.info(
        "[Node1] persona_factory 완료: 유저=%d명, 페르소나=%d개",
        len(user_data_list),
        len(persona_prompts),
    )
    return {
        "user_data_list": user_data_list,
        "persona_prompts": persona_prompts,
    }
