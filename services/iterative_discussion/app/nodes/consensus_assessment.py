import json
import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from services.iterative_discussion.app.engine.llm_factory import get_chat_llm
from services.iterative_discussion.app.utils.monitoring import create_langfuse_handler
from services.iterative_discussion.app.engine.state import ConsensusState
from services.iterative_discussion.app.prompts.consensus_templates import (
    CONSENSUS_ASSESSMENT_PROMPT,
    DEADLOCK_RESOLUTION_PROMPT,
)


def _format_candidate_list(candidate_pool: List[Dict[str, Any]]) -> str:
    """후보 식당 목록을 텍스트로 포맷."""
    lines = []
    for i, r in enumerate(candidate_pool, 1):
        name = r.get("place_name", "알 수 없음")
        category = r.get("category_detail", "")
        rid = str(r.get("_id", ""))
        lines.append(f"{i}. {name} ({category}) [id: {rid}]")
    return "\n".join(lines)


def _format_dialogue_history(dialogue_history: List[Dict[str, Any]]) -> str:
    """대화 기록을 텍스트로 포맷."""
    lines = []
    for entry in dialogue_history:
        nickname = entry.get("nickname", "익명")
        rd = entry.get("round", "?")
        content = entry.get("content", "")
        lines.append(f"[라운드{rd} - {nickname}]: {content}")
    return "\n".join(lines)


def _parse_llm_json(text: str) -> Dict[str, Any]:
    """LLM 응답에서 JSON을 추출. 마크다운 코드블록 처리 포함."""
    # 마크다운 코드블록 안의 JSON 추출
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _build_moderator_feedback(
    candidates: List[Dict[str, Any]],
    rejected: List[Dict[str, Any]],
    candidate_pool: List[Dict[str, Any]],
    target_count: int = 5,
) -> str:
    """합의 미달 시 사회자 피드백을 생성한다 (LLM 호출 없음)."""
    agreed_names = [c.get("place_name", "?") for c in candidates]
    rejected_ids = {r.get("restaurant_id", "") for r in rejected}
    agreed_ids = {c.get("restaurant_id", "") for c in candidates}
    excluded_ids = agreed_ids | rejected_ids

    # 아직 충분히 논의되지 않은 후보
    undiscussed = [
        r.get("place_name", "?")
        for r in candidate_pool
        if str(r.get("_id", "")) not in excluded_ids
    ]

    need = target_count - len(candidates)
    lines = ["[사회자 정리]"]
    if agreed_names:
        lines.append(
            f"- 현재까지 합의된 식당: {', '.join(agreed_names)} ({len(agreed_names)}개)"
        )
    else:
        lines.append("- 현재까지 합의된 식당이 없습니다.")
    lines.append(f"- {need}개 식당에 대한 추가 합의가 필요합니다.")
    if undiscussed:
        lines.append(
            f"- 아직 충분히 논의되지 않은 후보: {', '.join(undiscussed[:5])}"
        )
    if rejected:
        rejected_names = [r.get("place_name", "?") for r in rejected]
        lines.append(
            f"- 거부된 식당: {', '.join(rejected_names)} → 새로운 후보로 교체됩니다."
        )
    lines.append("- 다음 라운드에서 위 식당들에 대해 더 구체적으로 논의해주세요.")
    return "\n".join(lines)


async def consensus_assessment(state: ConsensusState) -> dict:
    """Node 4: 합의 도달 여부 판정 + 교착 시 강제 선정."""
    candidate_pool = state.get("candidate_pool", [])
    dialogue_history = state.get("dialogue_history", [])
    current_round = state.get("round", 0)
    max_rounds = state.get("max_rounds", 3)

    candidate_text = _format_candidate_list(candidate_pool)
    dialogue_text = _format_dialogue_history(dialogue_history)

    # 교착 상태 판단: max_rounds 도달 여부
    is_deadlock = current_round >= max_rounds

    if is_deadlock:
        prompt = DEADLOCK_RESOLUTION_PROMPT.format(
            candidate_list=candidate_text,
            dialogue_history=dialogue_text,
        )
    else:
        prompt = CONSENSUS_ASSESSMENT_PROMPT.format(
            candidate_list=candidate_text,
            dialogue_history=dialogue_text,
        )

    trace_id = state.get("langfuse_trace_id", "")

    llm = get_chat_llm(temperature=0.0)
    handler = create_langfuse_handler(
        trace_id=trace_id,
        name=f"assessment_round{current_round}{'_deadlock' if is_deadlock else ''}",
        metadata={"round": current_round, "is_deadlock": is_deadlock},
    )
    config = {"callbacks": [handler]} if handler else {}

    response = await llm.ainvoke(
        [HumanMessage(content=prompt)],
        config=config,
    )

    parsed = _parse_llm_json(response.content)

    if not parsed:
        # JSON 파싱 실패 시: 교착이면 강제 합의, 아니면 루프 계속
        if is_deadlock:
            fallback = [
                {
                    "restaurant_id": str(r.get("_id", "")),
                    "place_name": r.get("place_name", ""),
                    "reason": "교착 해소 — 초기 점수 기반 선정",
                }
                for r in candidate_pool[:5]
            ]
            return {
                "consensus_reached": True,
                "consensus_candidates": fallback,
            }
        return {"consensus_reached": False, "consensus_candidates": []}

    consensus_reached = parsed.get("consensus_reached", False)
    candidates = parsed.get("candidates", [])
    rejected = parsed.get("rejected", [])

    # 토론에서 거부된 식당 ID 목록
    rejected_ids = [r.get("restaurant_id", "") for r in rejected]

    # 교착 상태에서는 무조건 합의 처리
    if is_deadlock:
        consensus_reached = True

    # candidates에서 거부 목록에 포함된 식당 제거
    candidates = [
        c for c in candidates
        if c.get("restaurant_id", "") not in rejected_ids
    ]

    # 강화된 합의 기준: 5개 이상이어야 합의 도달 (교착 시 제외)
    if not is_deadlock and len(candidates) < 5:
        consensus_reached = False

    # 교착 시에만 보충 (일반 흐름에서는 보충하지 않음)
    if is_deadlock and len(candidates) < 5:
        existing_ids = {c.get("restaurant_id", "") for c in candidates}
        excluded_ids = existing_ids | set(rejected_ids)
        for r in candidate_pool:
            if len(candidates) >= 5:
                break
            rid = str(r.get("_id", ""))
            if rid not in excluded_ids:
                candidates.append({
                    "restaurant_id": rid,
                    "place_name": r.get("place_name", ""),
                    "reason": "초기 점수 기반 보충 선정",
                })
                excluded_ids.add(rid)

    # 합의 미달 시 사회자 피드백 생성
    moderator_feedback = ""
    if not consensus_reached and not is_deadlock:
        moderator_feedback = _build_moderator_feedback(
            candidates, rejected, candidate_pool,
        )

    return {
        "consensus_reached": consensus_reached,
        "consensus_candidates": candidates,
        "rejected_restaurant_ids": rejected_ids,
        "moderator_feedback": moderator_feedback,
    }
