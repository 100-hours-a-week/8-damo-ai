import logging
import time
from importlib.metadata import version
from typing import Any

from faststream import FastStream, Context
from langfuse import observe

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

from services.iterative_discussion.app.utils.logging_config import setup_logging

setup_logging()  # 반드시 monitoring import 전에 호출
logger = logging.getLogger(__name__)

import services.iterative_discussion.app.utils.monitoring  # noqa: F401 — Langfuse 환경변수 주입

from services.iterative_discussion.app.engine.graph import build_consensus_graph
from services.iterative_discussion.app.engine.state import create_initial_state

logger.info(
    "[Startup] langfuse==%s, langgraph==%s, langchain==%s",
    version("langfuse"),
    version("langgraph"),
    version("langchain"),
)

service = KafkaService()
broker = service.broker
app = FastStream(broker)


def _safe_int(value: Any) -> int:
    """문자열/숫자를 int로 안전하게 변환. 실패 시 0 반환."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _aggregate_persona_votes(
    persona_votes: list[dict[str, Any]],
) -> list[VoteResultData]:
    """per-user votes를 per-restaurant VoteResultData로 집계 변환."""
    restaurant_map: dict[str, dict[str, Any]] = {}

    for vote_entry in persona_votes:
        user_id = _safe_int(vote_entry.get("user_id", 0))
        for vote in vote_entry.get("votes", []):
            rid = vote.get("restaurant_id", "")
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


@broker.subscriber(service.get_ai_discussion_request_topic())
@observe(name="llm_talks")
async def handle_discussion_request(
    event: DiscussionRequestPayload,
    message=Context(),
) -> None:
    """discussion-request 토픽 메시지를 수신하여 합의 그래프를 실행한다."""
    key: bytes = message.raw_message.key
    event_id = event.event_id
    req = event.payload
    dining_id = req.dining_data.dining_id

    logger.info(
        "[START] discussion request 수신: dining_id=%s, event_id=%s, users=%s",
        dining_id,
        event_id,
        req.user_ids,
    )

    # 발언마다 recommendation-streaming 토픽에 publish 하는 콜백
    async def on_persona_speak(entry: dict) -> None:
        streaming_data = RecommendationStreamingData(
            dining_id=dining_id,
            user_id=_safe_int(entry.get("user_id", 0)),
            content=entry.get("content", ""),
        )
        payload = RecommendationStreamingPayload(
            event_id=event_id,
            event_type=EventType.RECOMMENDATION_STREAMING.value,
            payload=streaming_data,
        )
        await service.publish_recommendation_streaming(data=payload)

    # 그래프 실행
    initial_state = create_initial_state(
        user_ids=req.user_ids,
        dining_data=req.dining_data.model_dump(),
        filtered_restaurant_ids=req.filtered_restaurant,
        vote_result_list=[v.model_dump(by_alias=False) for v in req.vote_result_list],
    )
    graph = build_consensus_graph()
    config = {"configurable": {"on_persona_speak": on_persona_speak}}

    logger.info("[GRAPH] 합의 그래프 실행 시작: dining_id=%s", dining_id)
    t0 = time.monotonic()
    try:
        result = await graph.ainvoke(initial_state, config=config)
    except Exception:
        elapsed = time.monotonic() - t0
        logger.exception(
            "[GRAPH] 합의 그래프 실패: dining_id=%s (%.1fs 경과)", dining_id, elapsed
        )
        error_data = DiscussionResponseData(
            dining_id=dining_id,
            final_restaurant_ids=[],
            persona_vote_result_list=[],
        )
        await service.publish_ai_discussion_response(
            event_id=event_id,
            key=key,
            data=error_data,
        )
        return

    # 최종 결과: 5개 미만이면 candidate_pool에서 보충
    final_selection = list(result.get("final_selection", []))
    if len(final_selection) < 5:
        existing_ids = {item.get("restaurant_id", "") for item in final_selection}
        for r in result.get("candidate_pool", []):
            if len(final_selection) >= 5:
                break
            rid = str(r.get("_id", ""))
            if rid not in existing_ids:
                final_selection.append(
                    {
                        "restaurant_id": rid,
                        "reason": f"{r.get('place_name', '')} — 후보 풀 기반 보충 선정",
                    }
                )
                existing_ids.add(rid)

    response_data = DiscussionResponseData(
        dining_id=dining_id,
        final_restaurant_ids=[
            FinalRestaurant(
                restaurant_id=item.get("restaurant_id", ""),
                summary=item.get("reason", ""),
            )
            for item in final_selection
        ],
        persona_vote_result_list=_aggregate_persona_votes(
            result.get("persona_votes", [])
        ),
    )
    await service.publish_ai_discussion_response(
        event_id=event_id,
        key=key,
        data=response_data,
    )

    elapsed = time.monotonic() - t0
    logger.info(
        "[DONE] 합의 완료: dining_id=%s, 최종 선정=%d개, 소요=%.1fs",
        dining_id,
        len(response_data.final_restaurant_ids),
        elapsed,
    )
