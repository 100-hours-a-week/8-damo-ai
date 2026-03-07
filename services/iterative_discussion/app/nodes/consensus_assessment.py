import json
import logging
import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langfuse import get_client, observe
from services.iterative_discussion.app.prompts.langfuse_prompts import make_callback_handler

from services.iterative_discussion.app.engine.llm_factory import get_chat_llm
from services.iterative_discussion.app.engine.state import ConsensusState
from services.iterative_discussion.app.prompts.consensus_templates import (
    CONSENSUS_ASSESSMENT_PROMPT,
    DEADLOCK_RESOLUTION_PROMPT,
)
from services.iterative_discussion.app.prompts.langfuse_prompts import get_prompt
from shared.utils.config import settings


logger = logging.getLogger(__name__)


def _format_candidate_list(candidate_pool: List[Dict[str, Any]]) -> str:
    """후보 식당 목록을 텍스트로 포맷."""
    lines = []
    for i, r in enumerate(candidate_pool, 1):
        name = r.get("place_name", "알 수 없음")
        category = r.get("category_detail", "")
        rid = str(r.get("_id", ""))
        menus = r.get("menus", [])
        menu_text = ", ".join(
            f"{m.get('title', '')}({m.get('price', 0)}원)" for m in menus
        ) if menus else "메뉴 정보 없음"
        review_count = r.get("review_count", 0)
        keywords = r.get("restaurant_review_keywords", [])
        keyword_text = ", ".join(
            f"{k.get('keyword', '')}({k.get('count', 0)})" for k in keywords[:3]
        ) if keywords else "리뷰 없음"
        lines.append(
            f"{i}. {name} ({category}) [id: {rid}] | 메뉴: {menu_text} | "
            f"리뷰: {review_count}개, 키워드: {keyword_text}"
        )
    return "\n".join(lines)


def _format_dialogue_history(dialogue_history: List[Dict[str, Any]]) -> str:
    """대화 기록을 라운드별로 그룹화하여 텍스트로 포맷."""
    from itertools import groupby

    lines: List[str] = []
    sorted_history = sorted(dialogue_history, key=lambda e: e.get("round", 0))

    for rd, entries in groupby(sorted_history, key=lambda e: e.get("round", 0)):
        lines.append(f"── 라운드 {rd} ──")
        for entry in entries:
            nickname = entry.get("nickname", "익명")
            content = entry.get("content", "")
            lines.append(f"[{nickname}]: {content}")
        lines.append("")  # 라운드 간 빈 줄

    return "\n".join(lines).rstrip()


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
    # 방어적 필터: rejected를 현재 candidate_pool 기준으로 필터
    pool_ids = {str(r.get("_id", "")) for r in candidate_pool}
    rejected = [r for r in rejected if r.get("restaurant_id", "") in pool_ids]

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

    agreed_count = len(candidates)
    need = target_count - agreed_count
    lines = [f"[사회자 정리] 진행 현황: {agreed_count}/{target_count}"]
    if agreed_names:
        lines.append(
            f"- 현재까지 합의된 식당: {', '.join(agreed_names)} ({agreed_count}개)"
        )
    else:
        lines.append("- 현재까지 합의된 식당이 없습니다.")
    lines.append(f"- {need}개 식당에 대한 추가 합의가 필요합니다.")
    if undiscussed:
        lines.append(
            f"- 아직 논의되지 않은 후보가 {len(undiscussed)}개 있습니다: "
            f"{', '.join(undiscussed[:5])}"
        )
        lines.append("  → 이 식당들에 대해 각자 의견을 말씀해주세요.")
    if rejected:
        rejected_names = [r.get("place_name", "?") for r in rejected]
        lines.append(
            f"- 거부된 식당: {', '.join(rejected_names)} → 제외 후 새로운 후보로 교체 예정"
        )
    lines.append("- 다음 라운드에서 위 식당들에 대해 더 구체적으로 논의해주세요.")
    return "\n".join(lines)


@observe(name="consensus_assessment")
async def consensus_assessment(state: ConsensusState) -> dict:
    """Node 5: 합의 도달 여부 판정 + 교착 시 강제 선정."""
    candidate_pool = state.get("candidate_pool", [])
    dialogue_history = state.get("dialogue_history", [])
    current_round = state.get("round", 0)
    max_rounds = state.get("max_rounds", 3)
    logger.info(
        "[Node5] consensus_assessment 시작: round=%d/%d, 후보=%d개",
        current_round,
        max_rounds,
        len(candidate_pool),
    )

    candidate_text = _format_candidate_list(candidate_pool)
    dialogue_text = _format_dialogue_history(dialogue_history)

    # 교착 상태 판단: max_rounds 도달 여부
    is_deadlock = current_round >= max_rounds

    prompt_vars = {
        "candidate_list": candidate_text,
        "dialogue_history": dialogue_text,
        "current_round": current_round,
    }
    if is_deadlock:
        prompt, lf_prompt = get_prompt(
            "consensus-deadlock",
            DEADLOCK_RESOLUTION_PROMPT,
            **prompt_vars,
        )
    else:
        prompt, lf_prompt = get_prompt(
            "consensus-assessment",
            CONSENSUS_ASSESSMENT_PROMPT,
            **prompt_vars,
        )

    llm = get_chat_llm(temperature=0.0)
    get_client().update_current_span(metadata={"tags": ["consensus_assessment", settings.OPENAI_MODEL]})

    try:
        lf_handler = make_callback_handler()
        lf_config = {"callbacks": [lf_handler], "metadata": {"round": current_round, "is_deadlock": is_deadlock}}
        response = await llm.ainvoke([HumanMessage(content=prompt)], config=lf_config)
    except Exception:
        logger.warning("합의 판정 LLM 호출 실패", exc_info=True)
        parsed = {}
    else:
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
    raw_rejected = parsed.get("rejected", [])

    # 핵심 필터: rejected를 현재 candidate_pool에 있는 식당으로만 제한
    pool_ids = {str(r.get("_id", "")) for r in candidate_pool}
    rejected = [r for r in raw_rejected if r.get("restaurant_id", "") in pool_ids]

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

    logger.info(
        "[Node5] consensus_assessment 완료: reached=%s, candidates=%d, rejected=%d",
        consensus_reached,
        len(candidates),
        len(rejected_ids),
    )
    return {
        "consensus_reached": consensus_reached,
        "consensus_candidates": candidates,
        "rejected_restaurant_ids": rejected_ids,
        "moderator_feedback": moderator_feedback,
    }
