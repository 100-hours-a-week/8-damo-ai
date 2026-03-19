"""agent_dialogue 진입점 — gateway에서 직접 호출.

Kafka discussion 토픽 없이 gateway 프로세스 내에서 그래프를 실행한다.
"""
import logging
import time
from typing import Any, Callable, Coroutine

from langfuse import get_client as _get_lf_client

from services.agent_dialogue.app.utils.logging_config import setup_logging

setup_logging()  # monitoring import 전에 호출
logger = logging.getLogger(__name__)

import services.agent_dialogue.app.utils.monitoring  # noqa: F401 — Langfuse 환경변수 주입

from shared.database.db_manager import DBManager
from shared.schemas.stream_schema import (
    DiscussionRequestData,
    DiscussionResponseData,
    FinalRestaurant,
    VoteResultData,
)
from services.agent_dialogue.app.engine.graph import build_agent_dialogue_graph
from services.agent_dialogue.app.engine.state import create_initial_state


def _safe_int(value: Any) -> int:
    """문자열/숫자를 int로 안전하게 변환. 실패 시 0 반환."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


async def _save_persona_votes(dining_id: int, persona_votes: list[dict[str, Any]]) -> None:
    """persona_votes(flat 포맷)를 dining_sessions.phases에 push."""
    try:
        db = DBManager(col_name="dining_sessions")
        await db.update_one_with_command(
            {"diningId": dining_id},
            {"$push": {"phases": {"persona_votes": persona_votes}}},
            upsert=True,
        )
        logger.info("[SAVE] persona_votes 저장 완료: dining_id=%s", dining_id)
    except Exception:
        logger.warning("[SAVE] persona_votes 저장 실패: dining_id=%s", dining_id, exc_info=True)


def _aggregate_persona_votes(
    persona_votes: list[dict[str, Any]],
) -> list[VoteResultData]:
    """flat persona_votes를 per-restaurant VoteResultData로 집계 변환."""
    restaurant_map: dict[str, dict[str, Any]] = {}

    for vote in persona_votes:
        user_id = _safe_int(vote.get("user_id", 0))
        rid = str(vote.get("restaurant_id", ""))
        if not rid:
            continue
        if rid not in restaurant_map:
            restaurant_map[rid] = {
                "like_count": 0,
                "dislike_count": 0,
                "liked_user_ids": [],
                "disliked_user_ids": [],
            }
        entry = restaurant_map[rid]
        if vote.get("approve", False):
            entry["like_count"] += 1
            entry["liked_user_ids"].append(user_id)
        else:
            entry["dislike_count"] += 1
            entry["disliked_user_ids"].append(user_id)

    return [
        VoteResultData(
            restaurant_id=rid,
            like_count=data["like_count"],
            dislike_count=data["dislike_count"],
            liked_user_ids=data["liked_user_ids"],
            disliked_user_ids=data["disliked_user_ids"],
        )
        for rid, data in restaurant_map.items()
    ]


async def run_agent_dialogue(
    req: DiscussionRequestData,
    correlation_id: str,
    on_persona_speak: Callable[[dict], Coroutine] | None = None,
) -> DiscussionResponseData:
    """gateway에서 직접 호출하는 agent_dialogue 진입점.

    Kafka 없이 동일 프로세스에서 그래프를 실행하고 결과를 반환한다.
    correlation_id를 Langfuse session_id로 사용해 전체 흐름을 단일 세션으로 추적한다.
    """
    dining_id = req.dining_data.dining_id
    _get_lf_client().update_current_trace(session_id=correlation_id)

    initial_state = create_initial_state(
        user_ids=req.user_ids,
        dining_data=req.dining_data.model_dump(),
        filtered_restaurant_ids=req.filtered_restaurant,
        vote_result_list=[v.model_dump(by_alias=False) for v in (req.vote_result_list or [])],
    )
    config = {"configurable": {"on_persona_speak": on_persona_speak}}

    logger.info("[TASK] agent_dialogue 그래프 실행 시작: dining_id=%s", dining_id)
    t0 = time.monotonic()
    try:
        result = await build_agent_dialogue_graph().ainvoke(initial_state, config=config)
    except Exception:
        elapsed = time.monotonic() - t0
        logger.exception(
            "[TASK] agent_dialogue 그래프 실패: dining_id=%s (%.1fs)", dining_id, elapsed
        )
        return DiscussionResponseData(
            dining_id=dining_id,
            final_restaurant_ids=[],
            persona_vote_result_list=[],
        )

    # 5개 미만이면 processed_restaurants로 보충
    recommended = list(result.get("recommended_restaurants", []))
    if len(recommended) < 5:
        already_ids = {r["restaurant_id"] for r in recommended}
        extras = sorted(
            [r for r in result.get("processed_restaurants", []) if r["restaurant_id"] not in already_ids],
            key=lambda r: (r["approve_count"], r["score"]),
            reverse=True,
        )
        recommended = recommended + extras[: 5 - len(recommended)]
    final_selection = recommended[:5]

    await _save_persona_votes(dining_id, result.get("persona_votes", []))

    elapsed = time.monotonic() - t0
    logger.info(
        "[TASK] agent_dialogue 완료: dining_id=%s, 추천=%d개, 소요=%.1fs",
        dining_id,
        len(final_selection),
        elapsed,
    )

    return DiscussionResponseData(
        dining_id=dining_id,
        final_restaurant_ids=[
            FinalRestaurant(
                restaurant_id=r.get("restaurant_id", ""),
                summary=r.get("place_name", ""),
            )
            for r in final_selection
        ],
        persona_vote_result_list=_aggregate_persona_votes(result.get("persona_votes", [])),
    )
