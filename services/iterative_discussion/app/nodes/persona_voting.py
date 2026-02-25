import json
import logging
import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from services.iterative_discussion.app.engine.llm_factory import get_chat_llm
from services.iterative_discussion.app.engine.state import ConsensusState
from services.iterative_discussion.app.prompts.voting_templates import VOTING_PROMPT


logger = logging.getLogger(__name__)


def _format_candidate_list(candidates: List[Dict[str, Any]]) -> str:
    """합의된 후보 식당을 텍스트로 포맷."""
    lines = []
    for i, c in enumerate(candidates, 1):
        name = c.get("place_name", "알 수 없음")
        rid = c.get("restaurant_id", "")
        reason = c.get("reason", "")
        lines.append(f"{i}. {name} [id: {rid}] — {reason}")
    return "\n".join(lines)


def _format_dialogue_summary(dialogue_history: List[Dict[str, Any]]) -> str:
    """토론 내용을 요약 형태로 포맷."""
    if not dialogue_history:
        return "(토론 기록 없음)"
    lines = []
    for entry in dialogue_history:
        nickname = entry.get("nickname", "익명")
        content = entry.get("content", "")
        lines.append(f"[{nickname}]: {content}")
    return "\n".join(lines)


def _parse_llm_json(text: str) -> Dict[str, Any]:
    """LLM 응답에서 JSON 추출."""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _tally_votes(
    all_votes: List[Dict[str, Any]],
    consensus_candidates: List[Dict[str, Any]],
    candidate_pool: List[Dict[str, Any]],
    rejected_restaurant_ids: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """투표 집계 → 반대 > 찬성인 식당 제외 → 보충 → 최종 정렬.

    Args:
        rejected_restaurant_ids: 토론 단계에서 부정적으로 언급된 식당 ID 목록.

    Returns:
        정렬된 최종 Top 5 리스트 (approve_count, reject_count, initial_score 포함).
    """
    # 초기 점수 매핑: restaurant_id → score (candidate_pool에서)
    score_map: Dict[str, float] = {}
    for r in candidate_pool:
        rid = str(r.get("_id", ""))
        score_map[rid] = r.get("score", 0.0)

    # 토론에서 거부된 식당 ID
    dialogue_rejected: set[str] = set(rejected_restaurant_ids or [])

    # 식당별 찬성/반대 집계
    approve_counts: Dict[str, int] = {}
    reject_counts: Dict[str, int] = {}
    for vote_entry in all_votes:
        for vote in vote_entry.get("votes", []):
            rid = vote.get("restaurant_id", "")
            if vote.get("approve", False):
                approve_counts[rid] = approve_counts.get(rid, 0) + 1
            else:
                reject_counts[rid] = reject_counts.get(rid, 0) + 1

    # 반대 > 찬성인 식당 제외, 나머지만 결과에 추가
    results: List[Dict[str, Any]] = []
    for c in consensus_candidates:
        rid = c.get("restaurant_id", "")
        approves = approve_counts.get(rid, 0)
        rejects = reject_counts.get(rid, 0)
        if rejects > approves:
            continue
        results.append({
            "restaurant_id": rid,
            "place_name": c.get("place_name", ""),
            "approve_count": approves,
            "reject_count": rejects,
            "initial_score": score_map.get(rid, 0.0),
            "reason": c.get("reason", ""),
        })

    # 5개 미만이면 candidate_pool에서 초기 점수 순으로 보충
    if len(results) < 5:
        existing_ids = {r["restaurant_id"] for r in results}
        # 투표 반대 + 토론 거부 식당 모두 제외
        vote_rejected = {
            rid for rid, cnt in reject_counts.items()
            if cnt > approve_counts.get(rid, 0)
        }
        excluded_ids = existing_ids | vote_rejected | dialogue_rejected
        for r in candidate_pool:
            if len(results) >= 5:
                break
            rid = str(r.get("_id", ""))
            if rid not in excluded_ids:
                results.append({
                    "restaurant_id": rid,
                    "place_name": r.get("place_name", ""),
                    "approve_count": 0,
                    "reject_count": 0,
                    "initial_score": score_map.get(rid, 0.0),
                    "reason": "보충 선정 — 초기 점수 기반",
                })
                excluded_ids.add(rid)

    results.sort(key=lambda x: (x["approve_count"], x["initial_score"]), reverse=True)
    return results


async def persona_voting(state: ConsensusState) -> dict:
    """Node 5: 최종 5개 식당에 대한 페르소나 투표 + 순위 정렬."""
    persona_prompts = state.get("persona_prompts", {})
    consensus_candidates = state.get("consensus_candidates", [])
    dialogue_history = state.get("dialogue_history", [])
    candidate_pool = state.get("candidate_pool", [])
    user_data_list = state.get("user_data_list", [])

    if not consensus_candidates:
        return {"is_error": True, "error_message": "consensus_candidates가 비어있습니다."}

    # 유저 ID → 닉네임 매핑
    id_to_nickname: Dict[str, str] = {}
    for user in user_data_list:
        uid = str(user.get("id", ""))
        id_to_nickname[uid] = user.get("nickname", "익명")

    candidate_text = _format_candidate_list(consensus_candidates)
    dialogue_summary = _format_dialogue_summary(dialogue_history)

    llm = get_chat_llm(temperature=0.7)

    all_votes: List[Dict[str, Any]] = []

    for user_id, system_prompt in persona_prompts.items():
        nickname = id_to_nickname.get(user_id, "익명")

        user_prompt = VOTING_PROMPT.format(
            nickname=nickname,
            candidate_list=candidate_text,
            dialogue_summary=dialogue_summary,
        )

        try:
            response = await llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ])
        except Exception:
            logger.warning("투표 LLM 호출 실패: user_id=%s", user_id, exc_info=True)
            votes = []
        else:
            parsed = _parse_llm_json(response.content)
            votes = parsed.get("votes", [])

        # 파싱 실패 또는 LLM 호출 실패 시 전부 찬성으로 fallback
        if not votes:
            votes = [
                {
                    "restaurant_id": c.get("restaurant_id", ""),
                    "place_name": c.get("place_name", ""),
                    "approve": True,
                    "reasoning": "투표 파싱 실패 — 기본 찬성 처리",
                }
                for c in consensus_candidates
            ]

        all_votes.append({
            "user_id": user_id,
            "nickname": nickname,
            "votes": votes,
        })

    # 집계 + 정렬 (토론 단계 거부 목록 반영)
    rejected_restaurant_ids = state.get("rejected_restaurant_ids", [])
    final_selection = _tally_votes(
        all_votes, consensus_candidates, candidate_pool, rejected_restaurant_ids,
    )

    # 최종 결정 요약
    if final_selection:
        top = final_selection[0]
        final_decision = (
            f"최종 1위: {top['place_name']} "
            f"(찬성 {top['approve_count']}표, 점수 {top['initial_score']})"
        )
    else:
        final_decision = "최종 선정 실패"

    return {
        "persona_votes": all_votes,
        "final_selection": final_selection,
        "final_decision": final_decision,
    }
