import logging

from faststream import FastStream, Context

from shared.schemas.stream_schema import (
    ConsensusDialogueData,
    ConsensusRequestPayload,
    ConsensusResultData,
    ConsensusResultItem,
)
from shared.stream.service import KafkaService

from services.iterative_discussion.app.engine.graph import build_consensus_graph
from services.iterative_discussion.app.engine.state import create_initial_state

logger = logging.getLogger(__name__)

service = KafkaService()
broker = service.broker
app = FastStream(broker)


@broker.subscriber(service.get_consensus_request_topic())
async def handle_consensus_request(
    event: ConsensusRequestPayload,
    message=Context(),
) -> None:
    """consensus-request 토픽 메시지를 수신하여 합의 그래프를 실행한다."""
    key: bytes = message.raw_message.key
    event_id = event.event_id
    req = event.payload
    dining_id = req.dining_data.dining_id

    logger.info("Received consensus request: dining_id=%s, event_id=%s", dining_id, event_id)

    # 발언마다 consensus-dialogue 토픽에 publish 하는 콜백
    async def on_persona_speak(entry: dict) -> None:
        data = ConsensusDialogueData(
            dining_id=dining_id,
            user_id=entry.get("user_id", ""),
            content=entry.get("content", ""),
        )
        await service.publish_consensus_dialogue(event_id=event_id, key=key, data=data)

    # 그래프 실행
    initial_state = create_initial_state(
        user_ids=req.user_ids,
        dining_data=req.dining_data.model_dump(),
        filtered_restaurant_ids=req.filtered_restaurant_ids,
        max_rounds=req.max_rounds,
        min_rounds=req.min_rounds,
    )
    graph = build_consensus_graph()
    config = {"configurable": {"on_persona_speak": on_persona_speak}}

    try:
        result = await graph.ainvoke(initial_state, config=config)
    except Exception:
        logger.exception("Consensus graph failed: dining_id=%s", dining_id)
        error_data = ConsensusResultData(
            dining_id=dining_id,
            final_selection=[],
            final_decision="ERROR: consensus graph execution failed",
        )
        await service.publish_consensus_result(event_id=event_id, key=key, data=error_data)
        return

    # 최종 결과 publish
    result_data = ConsensusResultData(
        dining_id=dining_id,
        final_selection=[
            ConsensusResultItem(**item)
            for item in result.get("final_selection", [])
        ],
        final_decision=result.get("final_decision", ""),
    )
    await service.publish_consensus_result(event_id=event_id, key=key, data=result_data)

    logger.info("Consensus completed: dining_id=%s", dining_id)
