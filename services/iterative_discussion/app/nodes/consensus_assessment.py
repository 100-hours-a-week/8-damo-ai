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

    # 교착 상태에서는 무조건 합의 처리
    if is_deadlock:
        consensus_reached = True
        if not candidates:
            candidates = [
                {
                    "restaurant_id": str(r.get("_id", "")),
                    "place_name": r.get("place_name", ""),
                    "reason": "교착 해소 — 초기 점수 기반 선정",
                }
                for r in candidate_pool[:5]
            ]

    return {
        "consensus_reached": consensus_reached,
        "consensus_candidates": candidates,
    }
