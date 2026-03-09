import asyncio
import logging
from typing import Any, Dict, List

from langfuse import get_client, observe

from services.iterative_discussion.app.engine.llm_factory import get_chat_llm
from services.iterative_discussion.app.engine.state import ConsensusState
from services.iterative_discussion.app.prompts.dialogue_templates import (
    RESTAURANT_SUMMARIZER_CHAT_FALLBACK,
)
from services.iterative_discussion.app.prompts.langfuse_prompts import get_chat_prompt
from shared.utils.config import settings


logger = logging.getLogger(__name__)


def _build_prompt_vars(restaurant: Dict[str, Any]) -> Dict[str, str]:
    """식당 문서에서 프롬프트 변수 추출."""
    menus = restaurant.get("menus", [])
    menu_text = (
        ", ".join(m.get("title", "") for m in menus if m.get("title"))
        if menus
        else "메뉴 정보 없음"
    )

    amenities = restaurant.get("amenities", [])
    amenity_text = ", ".join(amenities) if amenities else "없음"

    keywords = restaurant.get("restaurant_review_keywords", [])
    if keywords:
        sorted_keywords = sorted(keywords, key=lambda k: k.get("count", 0), reverse=True)
        filtered = [k for k in sorted_keywords if k.get("count", 0) >= 50]
        selected = filtered if filtered else sorted_keywords[:3]
        keyword_text = ", ".join(k.get("keyword", "") for k in selected[:3] if k.get("keyword"))
    else:
        keyword_text = "없음"

    return {
        "place_name": restaurant.get("place_name", "알 수 없음"),
        "category_detail": restaurant.get("category_detail", ""),
        "menus": menu_text,
        "amenities": amenity_text,
        "keywords": keyword_text,
    }


@observe(name="restaurant_summarizer")
async def restaurant_summarizer(state: ConsensusState) -> dict:
    """Node 2.5: API LLM으로 candidate_pool 식당별 자연어 요약 생성.

    실패한 식당은 candidate_summaries에서 생략되며,
    multi_agent_dialogue에서 fallback 포맷으로 처리된다.
    """
    candidate_pool: List[Dict[str, Any]] = state.get("candidate_pool", [])

    if not candidate_pool:
        logger.warning("[restaurant_summarizer] candidate_pool이 비어있음 — 스킵")
        return {"candidate_summaries": {}}

    llm = get_chat_llm(temperature=0.3, local=False)

    @observe(as_type="generation")
    async def _call_llm(messages: list, lf_prompt: Any, rid: str) -> str:
        model_name = settings.OPENAI_MODEL
        get_client().update_current_generation(
            name="restaurant_summarizer_llm",
            model=model_name,
            metadata={"tags": ["restaurant_summarizer", model_name]},
            prompt=lf_prompt,
            input=[{"role": m.type, "content": m.content} for m in messages],
        )
        response = await llm.ainvoke(messages)
        usage_meta = response.usage_metadata or {}
        get_client().update_current_generation(
            output=response.content,
            usage_details={
                "input": usage_meta.get("input_tokens", 0),
                "output": usage_meta.get("output_tokens", 0),
                "total": usage_meta.get("total_tokens", 0),
            },
        )
        return response.content.strip()

    async def _summarize_one(restaurant: Dict[str, Any]) -> tuple[str, str | None]:
        rid = str(restaurant.get("_id", ""))
        try:
            prompt_vars = _build_prompt_vars(restaurant)
            messages, lf_prompt = get_chat_prompt(
                "restaurant-summarizer",
                RESTAURANT_SUMMARIZER_CHAT_FALLBACK,
                **prompt_vars,
            )
            summary = await _call_llm(messages, lf_prompt, rid)
            logger.info(
                "[restaurant_summarizer] 요약 완료: rid=%s, 길이=%d자",
                rid,
                len(summary),
            )
            return rid, summary
        except Exception:
            logger.warning(
                "[restaurant_summarizer] 요약 실패: rid=%s",
                rid,
                exc_info=True,
            )
            return rid, None

    results = await asyncio.gather(
        *[_summarize_one(r) for r in candidate_pool],
        return_exceptions=True,
    )

    summaries: Dict[str, str] = {}
    for result in results:
        if isinstance(result, Exception):
            logger.warning(
                "[restaurant_summarizer] gather 예외: %s", result, exc_info=False
            )
            continue
        rid, summary = result
        if summary:
            summaries[rid] = summary

    logger.info(
        "[restaurant_summarizer] 완료: %d/%d 식당 요약",
        len(summaries),
        len(candidate_pool),
    )
    return {"candidate_summaries": summaries}
