import inspect
import logging
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langfuse import get_client, observe

from services.iterative_discussion.app.engine.llm_factory import get_chat_llm
from services.iterative_discussion.app.engine.state import ConsensusState
from services.iterative_discussion.app.prompts.dialogue_templates import (
    DIALOGUE_CHAT_FALLBACK,
    FIRST_ROUND_CHAT_FALLBACK,
    GUIDED_ROUND_CHAT_FALLBACK,
)
from services.iterative_discussion.app.prompts.langfuse_prompts import get_chat_prompt
from shared.utils.config import settings


logger = logging.getLogger(__name__)


def _format_candidate_list(
    candidate_pool: List[Dict[str, Any]],
    summaries: Dict[str, str] | None = None,
) -> str:
    """후보 식당 목록을 텍스트로 포맷.

    summaries가 제공되고 해당 식당의 요약이 있으면 자연어 요약을 사용한다.
    요약이 없는 식당은 fallback 포맷(메뉴·키워드·편의시설)으로 출력한다.
    """
    lines = []
    for i, r in enumerate(candidate_pool, 1):
        rid = str(r.get("_id", ""))
        name = r.get("place_name", "알 수 없음")
        if summaries and rid in summaries:
            lines.append(f"{i}. {name}\n   {summaries[rid]}")
        else:
            category = r.get("category_detail", "")
            menus = r.get("menus", [])[:5]
            menu_text = (
                ", ".join(
                    f"{m.get('title', '')}({m.get('price', 0)}원)" for m in menus
                )
                if menus
                else "메뉴 정보 없음"
            )
            keywords = r.get("restaurant_review_keywords", [])
            keyword_text = (
                ", ".join(
                    f"{k.get('keyword', '')}({k.get('count', 0)})"
                    for k in keywords[:5]
                )
                if keywords
                else "리뷰 없음"
            )
            amenities = r.get("amenities", [])
            amenity_text = ", ".join(amenities) if amenities else ""
            parts = [
                f"{i}. {name} ({category})",
                f"   메뉴: {menu_text}",
                f"   키워드: {keyword_text}",
            ]
            if amenity_text:
                parts.append(f"   편의: {amenity_text}")
            lines.append("\n".join(parts))
    return "\n".join(lines)


def _format_dining_info(dining_data: Dict[str, Any]) -> str:
    """회식 정보(예산, 날짜)를 텍스트로 포맷."""
    budget = dining_data.get("budget") or dining_data.get("Budget", 0)
    dining_date = dining_data.get("dining_date") or dining_data.get("diningDate", "")
    parts = []
    if budget:
        parts.append(f"예산: {budget:,}원")
    if dining_date:
        date_str = (
            str(dining_date).split("T")[0]
            if "T" in str(dining_date)
            else str(dining_date)
        )
        parts.append(f"날짜: {date_str}")
    return " | ".join(parts) if parts else "회식 정보 없음"


def _build_previous_messages(
    dialogue_history: List[Dict[str, Any]],
    current_user_id: str,
) -> list[dict]:
    """대화 기록을 user/assistant role 메시지 리스트로 변환.

    현재 페르소나의 이전 발언 = assistant, 다른 페르소나 발언 = user.
    Langfuse Chat 프롬프트의 placeholder 변수로 주입된다.
    """
    messages = []
    for entry in dialogue_history:
        nickname = entry.get("nickname", "익명")
        content = entry.get("content", "")
        role = "assistant" if entry.get("user_id") == current_user_id else "user"
        messages.append({"role": role, "content": f"[{nickname}]: {content}"})
    return messages


@observe(name="multi_agent_dialogue")
async def multi_agent_dialogue(state: ConsensusState, config: RunnableConfig) -> dict:
    """Node 3: 각 페르소나가 rotations_per_round회 발언하는 토론 라운드.

    config["configurable"]["on_persona_speak"] 콜백이 있으면
    각 페르소나 발언 직후 호출하여 실시간 스트리밍을 지원한다.
    """
    # 실시간 콜백 추출 (없으면 무시) — sync/async 모두 지원
    configurable = (config or {}).get("configurable") or {}
    on_speak: Optional[Callable[[Dict[str, Any]], Union[None, Awaitable[None]]]] = (
        configurable.get(
            "on_persona_speak",
        )
    )

    persona_prompts = state.get("persona_prompts", {})
    candidate_pool = state.get("candidate_pool", [])
    dialogue_history = list(state.get("dialogue_history", []))
    messages = list(state.get("messages", []))
    current_round = state.get("round", 0)
    user_data_list = state.get("user_data_list", [])
    dining_data = state.get("dining_data", {})
    rotations = state.get("rotations_per_round", 2)

    logger.info(
        "[Node4] multi_agent_dialogue 시작: round=%d, personas=%d, rotations=%d",
        current_round + 1,
        len(persona_prompts),
        rotations,
    )
    if not persona_prompts:
        logger.warning("[Node4] persona_prompts가 비어있어 에러 반환")
        return {"is_error": True, "error_message": "persona_prompts가 비어있습니다."}

    # 유저 ID → 닉네임 매핑
    id_to_nickname: Dict[str, str] = {}
    for user in user_data_list:
        uid = str(user.get("id", ""))
        id_to_nickname[uid] = user.get("nickname", "익명")

    candidate_summaries = state.get("candidate_summaries", {})
    candidate_text = _format_candidate_list(candidate_pool, candidate_summaries)
    dining_info = _format_dining_info(dining_data)
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
        messages.append(
            AIMessage(
                content=f"[사회자]: {moderator_feedback}",
                name="moderator",
            )
        )
        if on_speak:
            result = on_speak(moderator_entry)
            if inspect.isawaitable(result):
                await result

    initial_history_len = len(dialogue_history)

    _type_to_role = {"human": "user", "system": "system", "ai": "assistant"}

    @observe(as_type="generation")
    async def _persona_speak(
        user_id: str,
        nickname: str,
        system_prompt: str,
        dialogue_messages: List,
        round_num: int,
        rotation: int,
        lf_prompt: Any = None,
    ) -> Optional[str]:
        """페르소나 발언 1건."""
        model_name = settings.LOCAL_MODEL or settings.OPENAI_MODEL
        get_client().update_current_generation(
            name="llm_chat",
            model=model_name,
            metadata={"tags": ["multi_agent_dialogue", model_name]},
            prompt=lf_prompt,
            input=[{"role": "system", "content": system_prompt}]
            + [
                {"role": _type_to_role.get(m.type, m.type), "content": m.content}
                for m in dialogue_messages
            ],
        )
        logger.info(
            "[Node4] LLM 호출: round=%d, rotation=%d, user_id=%s (%s)",
            round_num,
            rotation,
            user_id,
            nickname,
        )
        try:
            response = await llm.ainvoke(
                [SystemMessage(content=system_prompt)] + dialogue_messages
            )
        except Exception:
            logger.warning(
                "[Node4] LLM 호출 실패: round=%d, user_id=%s",
                round_num,
                user_id,
                exc_info=True,
            )
            return None
        usage_meta = response.usage_metadata or {}
        get_client().update_current_generation(
            output=response.content,
            usage_details={
                "input": usage_meta.get("input_tokens", 0),
                "output": usage_meta.get("output_tokens", 0),
                "total": usage_meta.get("total_tokens", 0),
            },
        )
        logger.info(
            "[Node4] LLM 응답 수신: user_id=%s, 길이=%d자",
            user_id,
            len(response.content),
        )
        return re.sub(r"^\[.+?\]:\s*", "", response.content).strip()

    for rotation in range(rotations):
        for user_id, system_prompt in persona_prompts.items():
            nickname = id_to_nickname.get(user_id, "익명")

            # 프롬프트 분기: 사회자 피드백(첫 rotation만) > 첫 라운드 > 일반
            is_first = current_round == 0 and len(dialogue_history) == 0
            if moderator_feedback and rotation == 0:
                prompt_vars = {
                    "dining_info": dining_info,
                    "candidate_list": candidate_text,
                    "previous_messages": _build_previous_messages(dialogue_history, user_id),
                    "moderator_feedback": moderator_feedback,
                }
                dialogue_messages, lf_prompt = get_chat_prompt(
                    "dialogue-guided", GUIDED_ROUND_CHAT_FALLBACK, **prompt_vars
                )
            elif is_first:
                prompt_vars = {
                    "dining_info": dining_info,
                    "candidate_list": candidate_text,
                }
                dialogue_messages, lf_prompt = get_chat_prompt(
                    "dialogue-first-round", FIRST_ROUND_CHAT_FALLBACK, **prompt_vars
                )
            else:
                prompt_vars = {
                    "dining_info": dining_info,
                    "candidate_list": candidate_text,
                    "previous_messages": _build_previous_messages(dialogue_history, user_id),
                }
                dialogue_messages, lf_prompt = get_chat_prompt(
                    "dialogue-general", DIALOGUE_CHAT_FALLBACK, **prompt_vars
                )

            content = await _persona_speak(
                user_id=user_id,
                nickname=nickname,
                system_prompt=system_prompt,
                dialogue_messages=dialogue_messages,
                round_num=current_round + 1,
                rotation=rotation + 1,
                lf_prompt=lf_prompt,
            )
            if content is None:
                continue

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
                result = on_speak(entry)
                if inspect.isawaitable(result):
                    await result

    new_entries = len(dialogue_history) - initial_history_len
    if new_entries == 0:
        logger.warning("[Node4] 모든 LLM 호출 실패: round=%d", current_round + 1)
        return {
            "is_error": True,
            "error_message": "모든 페르소나 LLM 호출이 실패했습니다.",
        }

    logger.info(
        "[Node4] multi_agent_dialogue 완료: round=%d → %d, 발언=%d건",
        current_round + 1,
        current_round + 1,
        new_entries,
    )
    return {
        "round": current_round + 1,
        "messages": messages,
        "dialogue_history": dialogue_history,
        "moderator_feedback": "",  # 소비 후 초기화
    }
