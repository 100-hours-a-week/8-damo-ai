import asyncio
import logging

from faststream import Context, Logger
from faststream.asgi import AsgiFastStream

from shared.utils.logging_config import setup_logging
from shared.stream.service import KafkaService
from shared.stream.transactional_publisher import (
    TransactionalPublisher,
    get_transactional_publisher,
    set_transactional_publisher,
)
from shared.checkpoint import init_checkpointer, close_checkpointer
from shared.database.db_manager import DBManager
from shared.schemas.stream_schema import (
    RecommendationRequestPayload,
    RecommendationRefreshRequestPayload,
    RecommendationResponseData,
    RecommendationResponsePayload,
    RecommendedItem,
    RestaurantConfirmedPayload,
    UserPersonaUpdatePayload,
    ReceiptOCRRequestPayload,
    RecommendationStreamingData,
    RecommendationStreamingPayload,
    EventType,
    TopicType,
)
from shared.schemas.user_data import UserData
from shared.schemas.update_persona_db_request import UpdatePersonaDBRequest
from shared.utils.config import get_settings

from services.core_service.modules.web_connections import (
    health_check,
    log_check,
    lightning_request,
)
from services.core_service.modules.persona.task import analyze_persona_task
from services.recommendation.task import recommendation_task
from services.recommendation.sub_graphs.fix import fix_task
from services.core_service.modules.ocr.service import GoogleVisionService

setup_logging()  # 반드시 다른 서비스 import 전에 호출

logger = logging.getLogger(__name__)

settings = get_settings()
service = KafkaService()
broker = service.broker
app = AsgiFastStream(
    broker,
    asgi_routes=[
        ("/ai/health_check", health_check),
        ("/ai/log_check", log_check),
        ("/ai/lightning_request", lightning_request),
    ],
)


@app.on_startup
async def on_startup() -> None:
    """앱 시작 시 LangGraph 체크포인터와 트랜잭셔널 프로듀서를 초기화한다."""
    await init_checkpointer(settings.CHECKPOINT_DB_PATH)

    publisher = TransactionalPublisher(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        transactional_id=settings.KAFKA_TRANSACTIONAL_ID,
        group_id=settings.KAFKA_GROUP_ID,
    )
    await publisher.start()
    set_transactional_publisher(publisher)
    logger.info("Gateway 초기화 완료: 체크포인터 + 트랜잭셔널 프로듀서")


@app.on_shutdown
async def on_shutdown() -> None:
    """앱 종료 시 리소스를 정리한다."""
    publisher = get_transactional_publisher()
    if publisher:
        await publisher.stop()
    await close_checkpointer()
    logger.info("Gateway 종료 완료")
#


# ── 1. 회식 추천 ─────────────────────────────────────────────────────────────
@broker.subscriber(
    service.get_recommendation_request_topic(),
    group_id=settings.KAFKA_GROUP_ID,
    # no_ack=True: FastStream이 핸들러 반환 후 consumer.commit()을 호출하지 않도록 한다.
    # 오프셋은 TransactionalPublisher.publish() 내 send_offsets_to_transaction으로 커밋된다.
    no_ack=True,
)
async def handle_recommendation(
    event: RecommendationRequestPayload, logger: Logger, message=Context()
):
    logger.info(
        "recommendation 요청 수신: dining_id=%s", event.payload.dining_data.dining_id
    )
    try:
        correlation_id = str(getattr(message, "correlation_id", "unknown"))
        dining_id = event.payload.dining_data.dining_id

        async def on_persona_speak(entry: dict) -> None:
            await service.publish_recommendation_streaming(
                data=RecommendationStreamingPayload(
                    event_id=event.event_id,
                    event_type=EventType.RECOMMENDATION_STREAMING.value,
                    payload=RecommendationStreamingData(
                        dining_id=dining_id,
                        user_id=int(entry.get("user_id", 0)),
                        content=entry.get("content", ""),
                    ),
                )
            )

        result = await recommendation_task(
            event.payload,
            correlation_id,
            "recommend",
            on_persona_speak=on_persona_speak,
        )
        if result is None:
            logger.error("recommendation_task returned None: dining_id=%s", dining_id)
            return

        db = DBManager()
        await db.save_dining_session(result)

        db.set_collection("dining_sessions")
        updated_doc = await db.update_phase_count(
            filter_query={"diningId": dining_id}, field_name="currentPhase"
        )
        current_count = updated_doc.get("currentPhase", 1) if updated_doc else 1

        items = [
            RecommendedItem(
                restaurant_id=r["restaurant_id"],
                reasoning_description=r.get("reason", r.get("place_name", "")),
            )
            for r in result.get("final_selection", [])
        ]
        response_payload = RecommendationResponsePayload(
            event_id=event.event_id,
            event_type=EventType.RECOMMENDATION_RESPONSE.value,
            payload=RecommendationResponseData(
                dining_id=dining_id,
                recommendation_count=current_count,
                recommended_items=items,
            ),
        )
        incoming_headers = list(dict(message.headers).items()) if message.headers else []
        raw = message.raw_message

        publisher = get_transactional_publisher()
        if publisher:
            # exactly-once: 응답 발행 + 컨슈머 오프셋 커밋을 단일 트랜잭션으로 처리
            await publisher.publish(
                topic=TopicType.RECOMMENDATION_RESPONSE.value,
                value=response_payload,
                key=raw.key,
                headers=incoming_headers,
                consumer_topic=raw.topic,
                consumer_partition=raw.partition,
                consumer_offset=raw.offset,
            )
        else:
            await service.publish_recommendation_response(
                event=event, message=message, data=response_payload.payload
            )

        logger.info(
            "recommendation 응답 발행 완료: dining_id=%s, items=%d개",
            dining_id,
            len(items),
        )
    except Exception:
        logger.exception("handle_recommendation 오류")
        raise


# ── 2. 회식 재추천 ───────────────────────────────────────────────────────────
@broker.subscriber(
    service.get_recommendation_refresh_request_topic(),
    group_id=settings.KAFKA_GROUP_ID,
    no_ack=True,
)
async def handle_recommendation_refresh(
    event: RecommendationRefreshRequestPayload, logger: Logger, message=Context()
):
    logger.info(
        "recommendation refresh 요청 수신: dining_id=%s",
        event.payload.dining_data.dining_id,
    )
    try:
        correlation_id = str(getattr(message, "correlation_id", "unknown"))
        dining_id = event.payload.dining_data.dining_id

        async def on_persona_speak(entry: dict) -> None:
            await service.publish_recommendation_streaming(
                data=RecommendationStreamingPayload(
                    event_id=event.event_id,
                    event_type=EventType.RECOMMENDATION_STREAMING.value,
                    payload=RecommendationStreamingData(
                        dining_id=dining_id,
                        user_id=int(entry.get("user_id", 0)),
                        content=entry.get("content", ""),
                    ),
                )
            )

        result = await recommendation_task(
            event.payload, correlation_id, "refresh", on_persona_speak=on_persona_speak
        )
        if result is None:
            logger.error(
                "recommendation_task returned None: dining_id=%s", dining_id
            )
            return

        db = DBManager()
        updated_session = await db.save_dining_session(result)
        current_count = updated_session.get("currentPhase", 1) if updated_session else 1

        items = [
            RecommendedItem(
                restaurant_id=r["restaurant_id"],
                reasoning_description=r.get("reason", r.get("place_name", "")),
            )
            for r in result.get("final_selection", [])
        ]
        response_payload = RecommendationResponsePayload(
            event_id=event.event_id,
            event_type=EventType.RECOMMENDATION_RESPONSE.value,
            payload=RecommendationResponseData(
                dining_id=dining_id,
                recommendation_count=current_count,
                recommended_items=items,
            ),
        )
        incoming_headers = list(dict(message.headers).items()) if message.headers else []
        raw = message.raw_message

        publisher = get_transactional_publisher()
        if publisher:
            await publisher.publish(
                topic=TopicType.RECOMMENDATION_RESPONSE.value,
                value=response_payload,
                key=raw.key,
                headers=incoming_headers,
                consumer_topic=raw.topic,
                consumer_partition=raw.partition,
                consumer_offset=raw.offset,
            )
        else:
            await service.publish_recommendation_response(
                event=event, message=message, data=response_payload.payload
            )

        logger.info(
            "recommendation refresh 응답 발행 완료: dining_id=%s, items=%d개",
            dining_id,
            len(items),
        )
    except Exception:
        logger.exception("handle_recommendation_refresh 오류")
        raise


# ── 4. 장소 확정 ─────────────────────────────────────────────────────────────
@broker.subscriber(
    service.get_restaurant_confirmed_topic(), group_id=settings.KAFKA_GROUP_ID
)
async def handle_restaurant_confirmed(
    event: RestaurantConfirmedPayload, logger: Logger, message=Context()
):
    logger.info(
        "restaurant confirmed: dining_id=%s", event.payload.dining_data.dining_id
    )
    try:
        await fix_task(event)
    except Exception:
        logger.exception("handle_restaurant_confirmed 오류")
        raise


# ── 5. 페르소나 업데이트 ──────────────────────────────────────────────────────
@broker.subscriber(
    service.get_user_persona_update_topic(), group_id=settings.KAFKA_GROUP_ID
)
async def handle_persona_update(
    event: UserPersonaUpdatePayload, logger: Logger, message=Context()
):
    logger.info("persona update 요청 수신: user_id=%s", event.payload.user_id)
    try:
        correlation_id = str(getattr(message, "correlation_id", "unknown"))
        payload = event.payload

        user_data = UserData(
            id=payload.user_id,
            nickname=payload.nickname,
            gender=payload.gender,
            age_group=payload.age_group,
            allergies=payload.allergies,
            like_food_categories_id=payload.like_foods,
            categories_id=payload.like_ingredients,
            other_characteristics=payload.other_characteristics or "",
        )
        db_request = UpdatePersonaDBRequest(user_data=user_data, review_data=[])
        await analyze_persona_task(db_request, logger, correlation_id)
    except Exception:
        logger.exception("handle_persona_update 오류")
        raise


# ── 6. OCR 요청 ──────────────────────────────────────────────────────────────
@broker.subscriber(
    service.get_receipt_ocr_request_topic(), group_id=settings.KAFKA_GROUP_ID
)
async def handle_receipt_ocr(
    event: ReceiptOCRRequestPayload, logger: Logger, message=Context()
):
    logger.info("receipt OCR 요청 수신")
    try:
        payload = event.payload
        logger.debug("ocr payload: %s", payload)
        google_service = GoogleVisionService()
        logger.debug("google vision client: %s", await google_service.check_client())

        # TODO: OCR 처리 및 응답 발행 미구현
        # await service.publish_receipt_ocr_response(payload, message)
    except Exception:
        logger.exception("handle_receipt_ocr 오류")
        raise


async def main():
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
