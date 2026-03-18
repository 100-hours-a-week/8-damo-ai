"""RAG reason node: 추천 이유 생성 후 final_selection 구성.

recommended_restaurants가 5개 미만이면 processed_restaurants로 보충한 뒤
rag_reason_task()를 호출해 각 식당의 추천 이유를 생성한다.
"""
import logging
import time
from typing import Any

from shared.schemas.stream_schema import FinalRestaurant
from services.recommendation.rag_reason import rag_reason_task
from services.recommendation.state import PipelineState

logger = logging.getLogger(__name__)

_GENERIC_REASON = "예산과 위치를 고려한 최적의 회식 장소입니다."


async def rag_reason_node(state: PipelineState) -> dict:
    """recommended_restaurants → 5개 보충 → RAG 추천 이유 생성 → final_selection."""
    dining_id = state.get("dining_id")
    dining_data = state.get("dining_data", {})

    recommended = list(state.get("recommended_restaurants", []))

    # 5개 미만이면 processed_restaurants로 보충 (점수 높은 순)
    if len(recommended) < 5:
        already_ids = {r.get("restaurant_id") for r in recommended}
        extras = sorted(
            [
                r for r in state.get("processed_restaurants", [])
                if r.get("restaurant_id") not in already_ids
            ],
            key=lambda r: (r.get("approve_count", 0), r.get("score", 0)),
            reverse=True,
        )
        recommended = recommended + extras[: 5 - len(recommended)]
        logger.info(
            "[RAG_REASON] 보충 후 후보 수: %d개 (extras=%d개)", len(recommended), len(extras)
        )

    final_candidates = recommended[:5]

    if not final_candidates:
        logger.warning("[RAG_REASON] 추천 후보 없음: dining_id=%s", dining_id)
        return {"final_selection": []}

    # FinalRestaurant 변환
    final_restaurants = [
        FinalRestaurant(
            restaurant_id=r.get("restaurant_id", ""),
            summary=r.get("place_name", ""),
        )
        for r in final_candidates
    ]

    dining_context: dict[str, Any] = {
        "budget": dining_data.get("budget", ""),
        "dining_date": str(dining_data.get("dining_date", "")),
        "member_count": len(state.get("user_ids", [])),
    }

    logger.info(
        "[RAG_REASON] 추천 이유 생성 시작: dining_id=%s, restaurants=%d개",
        dining_id,
        len(final_restaurants),
    )
    t0 = time.monotonic()

    try:
        reason_map = await rag_reason_task(final_restaurants, dining_context)
    except Exception:
        logger.warning(
            "[RAG_REASON] rag_reason_task 실패, fallback 사용: dining_id=%s",
            dining_id,
            exc_info=True,
        )
        reason_map = {}

    elapsed = time.monotonic() - t0
    logger.info(
        "[RAG_REASON] 추천 이유 생성 완료: dining_id=%s, 소요=%.1fs", dining_id, elapsed
    )

    final_selection = [
        {
            "restaurant_id": item.restaurant_id,
            "place_name": item.summary,
            "reason": reason_map.get(item.restaurant_id) or _GENERIC_REASON,
        }
        for item in final_restaurants
    ]

    return {"final_selection": final_selection}
