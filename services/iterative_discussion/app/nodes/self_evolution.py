import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from shared.database.db_manager import DBManager
from services.iterative_discussion.app.engine.state import ConsensusState

logger = logging.getLogger(__name__)

_FEEDBACK_FOOTER = "위 피드백을 참고하여, 이번 대화에서는 유저의 실제 취향에 더 가까운 의견을 내세요."
_FEEDBACK_MARKER = "## 이전 추천 피드백\n"


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
    """이전 추천의 persona_votes를 DB에서 조회."""
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
    """유저 한 명의 페르소나 예측 vs 실제 투표를 비교하여 맞춘/틀린 케이스 분류.

    Returns:
        (correct_list, incorrect_list) 튜플
    """
    try:
        uid_int = int(user_id) if user_id else 0
    except (ValueError, TypeError):
        return [], []
    correct: List[VoteComparison] = []
    incorrect: List[VoteComparison] = []

    # previous_votes에서 해당 유저의 투표 엔트리 찾기
    user_entry = None
    for entry in previous_votes:
        if str(entry.get("user_id", "")) == user_id:
            user_entry = entry
            break

    if not user_entry:
        return correct, incorrect

    for vote in user_entry.get("votes", []):
        rid = str(vote.get("restaurant_id", ""))
        actual = actual_map.get(rid)
        if not actual:
            continue

        predicted_approve = vote.get("approve", True)

        # 실제 반응 판단
        if uid_int in actual.get("liked", []):
            actual_approve = True
        elif uid_int in actual.get("disliked", []):
            actual_approve = False
        else:
            continue  # 투표 안 한 식당은 스킵

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


async def self_evolution(state: ConsensusState) -> dict:
    """재추천 시 이전 가상투표 vs 실제 투표를 비교하여 few-shot 피드백을 프롬프트에 주입."""
    try:
        vote_result_list = state.get("vote_result_list", [])
        if not vote_result_list:
            return {}  # 초기 추천이면 스킵

        dining_data = state.get("dining_data", {})
        persona_prompts = dict(state.get("persona_prompts", {}))

        dining_id = dining_data.get("diningId") or dining_data.get("dining_id")
        if not dining_id:
            return {}

        # DB에서 이전 가상투표 조회
        previous_votes = await _fetch_previous_votes(dining_id)
        if not previous_votes:
            return {}

        # 실제 투표 매핑 생성 (1회만)
        actual_map = _build_actual_map(vote_result_list)

        # 유저별로 맞춘/틀린 케이스 분류 → few-shot 텍스트 생성 → 프롬프트에 삽입
        updated = False
        for user_id in persona_prompts:
            correct, incorrect = _compare_votes(
                user_id, previous_votes, actual_map
            )
            feedback_text = _format_vote_feedback(correct, incorrect)

            if not feedback_text:
                continue

            prompt = persona_prompts[user_id]
            if _FEEDBACK_MARKER not in prompt:
                logger.warning(
                    "self_evolution: feedback marker not found for user=%s",
                    user_id,
                )
                continue

            persona_prompts[user_id] = prompt.replace(
                _FEEDBACK_MARKER,
                f"{_FEEDBACK_MARKER}{feedback_text}\n",
                1,  # 첫 번째 매칭만 교체
            )
            updated = True
            logger.info(
                "self_evolution: user=%s correct=%d incorrect=%d",
                user_id,
                len(correct),
                len(incorrect),
            )

        if not updated:
            return {}

        return {"persona_prompts": persona_prompts}
    except Exception:
        logger.warning("self_evolution 실패, 보정 스킵", exc_info=True)
        return {}
