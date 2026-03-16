import asyncio
import logging
import time
from typing import Any

import runpod

from services.agent_dialogue.app.engine.graph import build_agent_dialogue_graph
from services.agent_dialogue.app.engine.state import create_initial_state
from services.agent_dialogue.app.utils.logging_config import setup_logging
import services.agent_dialogue.app.utils.monitoring  # noqa: F401 — Langfuse 환경변수 주입
from shared.schemas.stream_schema import (
    DiscussionRequestPayload,
    DiscussionResponseData,
    EventType,
    FinalRestaurant,
    RecommendationStreamingData,
    RecommendationStreamingPayload,
    VoteResultData,
)
from shared.stream.service import KafkaService

setup_logging()
logger = logging.getLogger(__name__)

# 워커 재사용 시 재연결 방지를 위해 모듈 수준에서 초기화
_service: KafkaService | None = None


async def _get_service() -> KafkaService:
    global _service
    if _service is None:
        _service = KafkaService()
        await _service.broker.start()
    return _service


def _safe_int(value: Any) -> int:
    """문자열/숫자를 int로 안전하게 변환. 실패 시 0 반환."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


async def _save_persona_votes(dining_id: int, persona_votes: list[dict[str, Any]]) -> None:
    """persona_votes(flat 포맷)를 dining_sessions.phases에 push."""
    try:
        from shared.database.db_manager import DBManager

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


async def _process(job_input: dict) -> dict:
    service = await _get_service()
    event = DiscussionRequestPayload(**job_input)
    key = str(event.event_id).encode()
    req = event.payload
    dining_id = req.dining_data.dining_id

    logger.info(
        "[START] discussion request 수신: dining_id=%s, event_id=%s, users=%s",
        dining_id,
        event.event_id,
        req.user_ids,
    )

    async def on_persona_speak(entry: dict) -> None:
        streaming_data = RecommendationStreamingData(
            dining_id=dining_id,
            user_id=_safe_int(entry.get("user_id", 0)),
            content=entry.get("content", ""),
        )
        payload = RecommendationStreamingPayload(
            event_id=event.event_id,
            event_type=EventType.RECOMMENDATION_STREAMING.value,
            payload=streaming_data,
        )
        await service.publish_recommendation_streaming(data=payload)

    initial_state = create_initial_state(
        user_ids=req.user_ids,
        dining_data=req.dining_data.model_dump(),
        filtered_restaurant_ids=req.filtered_restaurant,
        vote_result_list=[v.model_dump(by_alias=False) for v in req.vote_result_list],
    )
    graph = build_agent_dialogue_graph()
    config = {"configurable": {"on_persona_speak": on_persona_speak}}

    t0 = time.monotonic()
    try:
        result = await graph.ainvoke(initial_state, config=config)
    except Exception:
        logger.exception("[GRAPH] 실패: dining_id=%s", dining_id)
        error_data = DiscussionResponseData(
            dining_id=dining_id,
            final_restaurant_ids=[],
            persona_vote_result_list=[],
        )
        await service.publish_ai_discussion_response(
            event_id=event.event_id, key=key, data=error_data
        )
        return {"status": "error", "dining_id": dining_id}

    recommended = list(result.get("recommended_restaurants", []))
    if len(recommended) < 5:
        already_ids = {r["restaurant_id"] for r in recommended}
        extras = sorted(
            [
                r
                for r in result.get("processed_restaurants", [])
                if r["restaurant_id"] not in already_ids
            ],
            key=lambda r: (r["approve_count"], r["score"]),
            reverse=True,
        )
        recommended = recommended + extras[: 5 - len(recommended)]

    final_selection = recommended[:5]

    response_data = DiscussionResponseData(
        dining_id=dining_id,
        final_restaurant_ids=[
            FinalRestaurant(
                restaurant_id=item.get("restaurant_id", ""),
                summary=item.get("place_name", ""),
            )
            for item in final_selection
        ],
        persona_vote_result_list=_aggregate_persona_votes(result.get("persona_votes", [])),
    )
    await service.publish_ai_discussion_response(
        event_id=event.event_id, key=key, data=response_data
    )
    await _save_persona_votes(dining_id, result.get("persona_votes", []))

    elapsed = time.monotonic() - t0
    logger.info(
        "[DONE] dining_id=%s, 추천=%d개, 소요=%.1fs", dining_id, len(final_selection), elapsed
    )
    return {"status": "ok", "dining_id": dining_id}


def handler(job: dict) -> dict:
    return asyncio.run(_process(job["input"]))


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
