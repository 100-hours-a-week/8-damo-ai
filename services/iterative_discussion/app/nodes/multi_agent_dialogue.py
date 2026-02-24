from typing import Any, Callable, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from services.iterative_discussion.app.engine.llm_factory import get_chat_llm
from services.iterative_discussion.app.engine.state import ConsensusState
from services.iterative_discussion.app.prompts.dialogue_templates import (
    DIALOGUE_USER_PROMPT,
    FIRST_ROUND_USER_PROMPT,
    GUIDED_ROUND_USER_PROMPT,
)


def _format_candidate_list(candidate_pool: List[Dict[str, Any]]) -> str:
    """후보 식당 목록을 텍스트로 포맷."""
    lines = []
    for i, r in enumerate(candidate_pool, 1):
        name = r.get("place_name", "알 수 없음")
        category = r.get("category_detail", "")
        score = r.get("score", 0)
        lines.append(f"{i}. {name} ({category}) [점수: {score}]")
    return "\n".join(lines)


def _format_previous_messages(dialogue_history: List[Dict[str, Any]]) -> str:
    """이전 대화 기록을 텍스트로 포맷."""
    if not dialogue_history:
        return "(아직 대화 없음)"
    lines = []
    for entry in dialogue_history:
        nickname = entry.get("nickname", "익명")
        content = entry.get("content", "")
        lines.append(f"[{nickname}]: {content}")
    return "\n".join(lines)


async def multi_agent_dialogue(state: ConsensusState, config: RunnableConfig) -> dict:
    """Node 3: 각 페르소나가 1회 발언하는 토론 라운드.

    config["configurable"]["on_persona_speak"] 콜백이 있으면
    각 페르소나 발언 직후 호출하여 실시간 스트리밍을 지원한다.
    """
    # 실시간 콜백 추출 (없으면 무시)
    configurable = (config or {}).get("configurable") or {}
    on_speak: Optional[Callable[[Dict[str, Any]], None]] = configurable.get(
        "on_persona_speak",
    )

    persona_prompts = state.get("persona_prompts", {})
    candidate_pool = state.get("candidate_pool", [])
    dialogue_history = list(state.get("dialogue_history", []))
    messages = list(state.get("messages", []))
    current_round = state.get("round", 0)
    user_data_list = state.get("user_data_list", [])

    if not persona_prompts:
        return {"is_error": True, "error_message": "persona_prompts가 비어있습니다."}

    # 유저 ID → 닉네임 매핑
    id_to_nickname: Dict[str, str] = {}
    for user in user_data_list:
        uid = str(user.get("id", ""))
        id_to_nickname[uid] = user.get("nickname", "익명")

    candidate_text = _format_candidate_list(candidate_pool)
    llm = get_chat_llm(temperature=0.7, local=True)

    # 사회자 피드백이 있으면 dialogue_history에 추가
    moderator_feedback = state.get("moderator_feedback", "")
    if moderator_feedback:
        moderator_entry = {
            "user_id": "moderator",
            "nickname": "사회자",
            "round": current_round + 1,
            "content": moderator_feedback,
        }
        dialogue_history.append(moderator_entry)
        messages.append(AIMessage(
            content=f"[사회자]: {moderator_feedback}",
            name="moderator",
        ))
        if on_speak:
            on_speak(moderator_entry)

    for user_id, system_prompt in persona_prompts.items():
        nickname = id_to_nickname.get(user_id, "익명")
        previous_text = _format_previous_messages(dialogue_history)

        # 프롬프트 분기: 사회자 피드백 > 첫 라운드 > 일반
        is_first = current_round == 0 and len(dialogue_history) == 0
        if moderator_feedback:
            user_prompt = GUIDED_ROUND_USER_PROMPT.format(
                candidate_list=candidate_text,
                previous_messages=previous_text,
                moderator_feedback=moderator_feedback,
            )
        elif is_first:
            user_prompt = FIRST_ROUND_USER_PROMPT.format(
                candidate_list=candidate_text,
            )
        else:
            user_prompt = DIALOGUE_USER_PROMPT.format(
                candidate_list=candidate_text,
                previous_messages=previous_text,
            )

        llm_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await llm.ainvoke(llm_messages)
        content = response.content

        # 대화 기록에 추가
        entry = {
            "user_id": user_id,
            "nickname": nickname,
            "round": current_round + 1,
            "content": content,
        }
        dialogue_history.append(entry)
        messages.append(AIMessage(content=f"[{nickname}]: {content}", name=user_id))

        if on_speak:
            on_speak(entry)

    return {
        "round": current_round + 1,
        "messages": messages,
        "dialogue_history": dialogue_history,
        "moderator_feedback": "",  # 소비 후 초기화
    }
