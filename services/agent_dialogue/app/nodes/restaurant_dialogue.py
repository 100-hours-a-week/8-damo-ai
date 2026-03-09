import json
import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langfuse import observe

from services.agent_dialogue.app.engine.state import AgentDialogueState
from services.agent_dialogue.app.engine.llm_factory import get_chat_llm
from services.agent_dialogue.app.prompts.langfuse_prompts import (
    get_chat_prompt,
    get_prompt,
    make_callback_handler,
)
from services.agent_dialogue.app.prompts.restaurant_templates import (
    ANALYST_SPEAK_PROMPT,
    ANALYST_SYSTEM_PROMPT,
    PERSONA_REACT_CHAT_FALLBACK,
    PERSONA_VOTE_CHAT_FALLBACK,
)

logger = logging.getLogger(__name__)


# ── 데이터 포맷 ────────────────────────────────────────────────────────────


def _format_dining_info(dining_data: Dict[str, Any]) -> str:
    """회식 정보를 텍스트로 포맷."""
    lines = []
    if dining_data.get("name"):
        lines.append(f"회식명: {dining_data['name']}")
    if dining_data.get("date"):
        lines.append(f"날짜: {dining_data['date']}")
    if dining_data.get("budget"):
        lines.append(f"1인당 예산: {dining_data['budget']:,}원")
    if dining_data.get("headcount"):
        lines.append(f"인원: {dining_data['headcount']}명")
    location_name = dining_data.get("location_name") or dining_data.get("locationName")
    if location_name:
        lines.append(f"회식 장소: {location_name}")
    return "\n".join(lines) if lines else "정보 없음"


def _calc_distance(
    restaurant: Dict[str, Any],
    dining_data: Dict[str, Any],
) -> Optional[float]:
    """식당과 회식 좌표 간 거리 계산 (좌표계 거리)."""
    try:
        rx = float(restaurant.get("x") or 0)
        ry = float(restaurant.get("y") or 0)
        dx = float(dining_data.get("x") or dining_data.get("longitude") or 0)
        dy = float(dining_data.get("y") or dining_data.get("latitude") or 0)
        if not (rx and ry and dx and dy):
            return None
        return round(math.sqrt((rx - dx) ** 2 + (ry - dy) ** 2), 6)
    except (TypeError, ValueError):
        return None


def _format_restaurant_info(
    restaurant: Dict[str, Any],
    dining_data: Dict[str, Any],
) -> Tuple[str, str]:
    """식당 데이터 전체를 포맷하여 (restaurant_info, allergy_info) 반환."""
    lines = []

    lines.append(f"식당명: {restaurant.get('place_name', '?')}")
    lines.append(f"카테고리: {restaurant.get('category_detail', '?')}")

    # 메뉴 (상위 10개)
    menus = restaurant.get("menus", [])
    if menus:
        menu_lines = []
        for m in menus[:10]:
            title = m.get("title", "?")
            price = m.get("price")
            menu_lines.append(f"  - {title}" + (f" ({price:,}원)" if price else ""))
        lines.append("메뉴:\n" + "\n".join(menu_lines))

    # 리뷰 키워드 (상위 5개)
    keywords = restaurant.get("review_keywords") or restaurant.get("restaurantReviewKeywords") or []
    if keywords:
        kw_list = [k.get("keyword", k) if isinstance(k, dict) else str(k) for k in keywords[:5]]
        lines.append(f"리뷰 키워드: {', '.join(kw_list)}")
    review_count = restaurant.get("review_count") or restaurant.get("reviewCount")
    if review_count:
        lines.append(f"리뷰 수: {review_count}개")

    # 편의시설
    amenities = restaurant.get("amenities", [])
    if amenities:
        lines.append(f"편의시설: {', '.join(str(a) for a in amenities)}")

    # 거리
    dist = _calc_distance(restaurant, dining_data)
    if dist is not None:
        lines.append(f"회식 장소까지 거리: {dist} (좌표 거리)")

    # 알레르기 정보 (별도 반환)
    all_menu_titles = " ".join(m.get("title", "") for m in menus)
    allergy_info = f"식당 메뉴 전체: {all_menu_titles}" if all_menu_titles else "메뉴 정보 없음"

    return "\n".join(lines), allergy_info


def _format_allergy_info(
    user_data_list: List[Dict[str, Any]],
    allergy_info: str,
) -> str:
    """참여자 알레르기 목록 + 식당 메뉴 정보를 합산."""
    lines = []
    for user in user_data_list:
        nickname = user.get("nickname", "?")
        allergies = user.get("allergies", [])
        if allergies:
            lines.append(f"- {nickname}: {', '.join(allergies)}")
    if not lines:
        lines.append("알레르기 정보 없음")
    lines.append(f"\n{allergy_info}")
    return "\n".join(lines)


def _get_nickname(user_id: str, user_data_list: List[Dict[str, Any]]) -> str:
    """user_id로 닉네임 조회. 없으면 user_id 반환."""
    for user in user_data_list:
        if str(user.get("id", "")) == user_id:
            return user.get("nickname", user_id)
    return user_id


# ── LLM 호출 ──────────────────────────────────────────────────────────────


@observe(as_type="generation")
async def _analyst_speak(
    restaurant_info: str,
    dining_info: str,
    allergy_info: str,
) -> str:
    """통합 분석가 발언 생성 (API LLM)."""
    llm = get_chat_llm(temperature=0.3, local=False)
    user_prompt, lf_prompt = get_prompt(
        "restaurant-analyst-speak",
        ANALYST_SPEAK_PROMPT,
        restaurant_info=restaurant_info,
        dining_info=dining_info,
        allergy_info=allergy_info,
    )
    cb = make_callback_handler()
    cfg = {"callbacks": [cb]} if lf_prompt is None else {"callbacks": [cb], "metadata": {"prompt": lf_prompt}}
    response = await llm.ainvoke(
        [SystemMessage(content=ANALYST_SYSTEM_PROMPT), HumanMessage(content=user_prompt)],
        config=cfg,
    )
    return str(response.content)


@observe(as_type="generation")
async def _persona_react(
    system_prompt: str,
    analyst_speech: str,
    previous_reactions: str,
) -> str:
    """페르소나 반응 생성 (로컬 LLM)."""
    llm = get_chat_llm(temperature=0.7, local=True)
    messages, lf_prompt = get_chat_prompt(
        "restaurant-persona-react",
        PERSONA_REACT_CHAT_FALLBACK,
        analyst_speech=analyst_speech,
        previous_reactions=previous_reactions,
    )
    cb = make_callback_handler()
    cfg = {"callbacks": [cb]} if lf_prompt is None else {"callbacks": [cb], "metadata": {"prompt": lf_prompt}}
    response = await llm.ainvoke([SystemMessage(content=system_prompt)] + messages, config=cfg)
    return str(response.content)


def _parse_vote_response(text: str) -> Dict[str, Any]:
    """JSON 투표 응답 파싱. 실패 시 approve=False 반환."""
    # ```json ... ``` 블록 추출 시도
    json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    raw = json_match.group(1) if json_match else text.strip()

    try:
        data = json.loads(raw)
        return {
            "approve": bool(data.get("approve", False)),
            "reasoning": str(data.get("reasoning", "")),
        }
    except (json.JSONDecodeError, AttributeError):
        logger.warning("투표 JSON 파싱 실패: %s", text[:100])
        return {"approve": False, "reasoning": "파싱 실패"}


@observe(as_type="generation")
async def _persona_vote(
    system_prompt: str,
    analyst_speech: str,
    all_reactions: str,
) -> Dict[str, Any]:
    """페르소나 투표 생성 (로컬 LLM, temperature=0.0)."""
    llm = get_chat_llm(temperature=0.0, local=True)
    messages, lf_prompt = get_chat_prompt(
        "restaurant-persona-vote",
        PERSONA_VOTE_CHAT_FALLBACK,
        analyst_speech=analyst_speech,
        all_reactions=all_reactions,
    )
    cb = make_callback_handler()
    cfg = {"callbacks": [cb]} if lf_prompt is None else {"callbacks": [cb], "metadata": {"prompt": lf_prompt}}
    response = await llm.ainvoke([SystemMessage(content=system_prompt)] + messages, config=cfg)
    return _parse_vote_response(str(response.content))


# ── 메인 노드 ──────────────────────────────────────────────────────────────


@observe(name="restaurant_dialogue")
async def restaurant_dialogue(state: AgentDialogueState) -> dict:
    """Node 3: 식당 1개에 대해 분석가 발언 → 페르소나 반응 → 페르소나 투표를 진행.

    과반수 찬성 시 recommended_restaurants에 추가.
    """
    restaurant_index = state.get("restaurant_index", 0)
    candidate_pool = state.get("candidate_pool", [])

    if restaurant_index >= len(candidate_pool):
        logger.error(
            "[Node3] restaurant_index=%d가 candidate_pool 크기=%d를 초과",
            restaurant_index,
            len(candidate_pool),
        )
        return {"is_error": True, "error_message": "restaurant_index 범위 초과"}

    restaurant = candidate_pool[restaurant_index]
    restaurant_id = str(restaurant.get("_id", ""))
    place_name = restaurant.get("place_name", "?")
    logger.info(
        "[Node3] restaurant_dialogue 시작: index=%d, place_name=%s",
        restaurant_index,
        place_name,
    )

    dining_data = state.get("dining_data", {})
    user_data_list = state.get("user_data_list", [])
    persona_prompts = state.get("persona_prompts", {})
    dialogue_history = list(state.get("dialogue_history", []))

    # 1. 식당 데이터 포맷
    restaurant_info, raw_allergy = _format_restaurant_info(restaurant, dining_data)
    allergy_info = _format_allergy_info(user_data_list, raw_allergy)
    dining_info = _format_dining_info(dining_data)

    # 2. 분석가 발언 생성 (API LLM)
    try:
        analyst_speech = await _analyst_speak(restaurant_info, dining_info, allergy_info)
    except Exception:
        logger.warning("[Node3] 분석가 발언 생성 실패", exc_info=True)
        return {"is_error": True, "error_message": f"분석가 발언 생성 실패: {place_name}"}

    dialogue_history.append({
        "type": "analyst",
        "restaurant_id": restaurant_id,
        "place_name": place_name,
        "content": analyst_speech,
    })

    # 3. 각 페르소나 순차 반응 (로컬 LLM)
    previous_reactions = ""
    for user_id, system_prompt in persona_prompts.items():
        nickname = _get_nickname(user_id, user_data_list)
        try:
            content = await _persona_react(system_prompt, analyst_speech, previous_reactions)
        except Exception:
            logger.warning("[Node3] 페르소나 반응 실패: user_id=%s", user_id, exc_info=True)
            content = "(반응 실패)"

        previous_reactions += f"[{nickname}]: {content}\n"
        dialogue_history.append({
            "type": "reaction",
            "restaurant_id": restaurant_id,
            "user_id": user_id,
            "nickname": nickname,
            "content": content,
        })

    # 4. 각 페르소나 투표 (로컬 LLM)
    all_reactions = previous_reactions
    vote_results = []
    for user_id, system_prompt in persona_prompts.items():
        nickname = _get_nickname(user_id, user_data_list)
        try:
            vote = await _persona_vote(system_prompt, analyst_speech, all_reactions)
        except Exception:
            logger.warning("[Node3] 페르소나 투표 실패: user_id=%s", user_id, exc_info=True)
            vote = {"approve": False, "reasoning": "투표 실패"}

        vote_results.append({
            "user_id": user_id,
            "nickname": nickname,
            "restaurant_id": restaurant_id,
            "place_name": place_name,
            **vote,
        })
        dialogue_history.append({
            "type": "vote",
            "restaurant_id": restaurant_id,
            "user_id": user_id,
            "nickname": nickname,
            "approve": vote["approve"],
            "reasoning": vote["reasoning"],
        })

    # 5. 과반수 판정
    approve_count = sum(1 for v in vote_results if v["approve"])
    total_count = len(vote_results)
    is_approved = total_count > 0 and approve_count > total_count / 2

    recommended = list(state.get("recommended_restaurants", []))
    if is_approved:
        recommended.append({
            "restaurant_id": restaurant_id,
            "place_name": place_name,
        })
        logger.info(
            "[Node3] %s 추천 등록: 찬성=%d/%d (누적=%d개)",
            place_name,
            approve_count,
            total_count,
            len(recommended),
        )
    else:
        logger.info(
            "[Node3] %s 미추천: 찬성=%d/%d",
            place_name,
            approve_count,
            total_count,
        )

    # 6. processed_restaurants 누적
    processed = list(state.get("processed_restaurants", []))
    processed.append({
        "restaurant_id": restaurant_id,
        "place_name": place_name,
        "approve_count": approve_count,
        "total_count": total_count,
        "score": restaurant.get("score", 0),
    })

    # 7. persona_votes 누적
    persona_votes = list(state.get("persona_votes", [])) + vote_results

    return {
        "restaurant_index": restaurant_index + 1,
        "dialogue_history": dialogue_history,
        "recommended_restaurants": recommended,
        "processed_restaurants": processed,
        "persona_votes": persona_votes,
    }
