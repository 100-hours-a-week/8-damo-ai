from faststream import ExceptionMiddleware, Context
from typing import Awaitable, Callable
from faststream.kafka import KafkaBroker, KafkaMessage
from aiokafka import ConsumerRecord
import dataclasses

from shared.schemas.stream_schema import (
    RecommendationRequestPayload,
    RecommendationResponseData,
    RecommendationResponsePayload,
    RecommendationStreamingData,
    RecommendationStreamingPayload,
    DiscussionRequestPayload,
    DiscussionRequestData,
    DiscussionResponseData,
    DiscussionResponsePayload,
    EventType,
    TopicType,
)
from shared.utils.config import get_settings


# 커스텀 파서
async def safe_header_parser(
    msg: ConsumerRecord,
    original_parser: Callable[[ConsumerRecord], Awaitable[KafkaMessage]],
) -> KafkaMessage:
    safe_headers = []

    # Kafka 원본 메시지(ConsumerRecord)에 헤더가 존재하는지 확인
    if msg.headers:
        for key, value in msg.headers:
            if key == "elasticapmtraceparent":
                continue  # (여기 아래 로직 안타고 다음 헤더로 넘어감)
            if isinstance(value, bytes):
                safe_value = value.decode("utf-8", errors="ignore").encode("utf-8")
                safe_headers.append((key, safe_value))
            else:
                safe_headers.append((key, value))

    # ConsumerRecord는 namedtuple이므로 _replace를 사용해 헤더만 안전한 값으로 교체합니다.
    safe_msg = dataclasses.replace(msg, headers=tuple(safe_headers))
    return await original_parser(safe_msg)


class KafkaService:
    """
    카프카 연결을 위한 추상화 클래스
    """

    def __init__(self):
        self.settings = get_settings()
        self.middleware = ExceptionMiddleware()
        self.broker = KafkaBroker(
            self.settings.KAFKA_BOOTSTRAP_SERVERS,
            middlewares=[self.middleware],
            parser=safe_header_parser,
            client_id=self.settings.KAFKA_CLIENT_ID,
        )
        self._recommendation_response_publisher = self.broker.publisher(
            TopicType.RECOMMENDATION_RESPONSE.value
        )
        self._recommendation_streaming_publisher = self.broker.publisher(
            TopicType.RECOMMENDATION_STREAMING.value
        )
        self._discussion_request_publisher = self.broker.publisher(
            TopicType.DISCUSSION_REQUEST.value
        )
        self._discussion_response_publisher = self.broker.publisher(
            TopicType.DISCUSSION_RESPONSE.value
        )
        self.error_handler()

    async def publish_recommendation_response(
        self,
        event: RecommendationRequestPayload,
        message: KafkaMessage,
        data: RecommendationResponseData,
    ):
        resp_data = RecommendationResponsePayload(
            event_id=event.event_id,
            event_type=EventType.RECOMMENDATION_RESPONSE.value,
            payload=data,
        )

        incoming_headers = dict(message.headers) if message.headers else {}

        await self._recommendation_response_publisher.publish(
            headers=incoming_headers, message=resp_data, key=message.raw_message.key
        )
        print(
            f"Service: Published recommendation response for key {message.raw_message.key.decode('utf-8') if message.raw_message.key else 'None'}"
        )

    async def publish_recommendation_streaming(
        self, event_id: int, data: RecommendationStreamingData,
    ):
        payload = RecommendationStreamingPayload(
            event_id=event_id,
            event_type=EventType.RECOMMENDATION_STREAMING.value,
            payload=data,
        )
        await self._recommendation_streaming_publisher.publish(
            message=data, key=f"{data.dining_id}-{data.user_id}".encode("utf-8")
        )
        print(
            f"Service: Published recommendation streaming for key {data.dining_id}-{data.user_id}"
        )
    
    async def publish_ai_discussion_request(self, event: RecommendationRequestPayload, message: KafkaMessage):
        incoming_headers = dict(message.headers) if message.headers else {}
        
        # 키 값 안전하게 추출
        raw_key = message.raw_message.key
        display_key = raw_key.decode('utf-8', errors='ignore') if raw_key else 'None'
        
        data = DiscussionRequestData(
            dining_data=event.payload.dining_data,
            user_ids=event.payload.user_ids,
            filtered_restaurant=[
                "6976b54010e1fa815903d4ce",
                "6976b57f10e1fa815903d4cf",
                "6976b58610e1fa815903d4d0",
                "6976b8b9fb8d6fe1764695b6",
                "6976b8bafb8d6fe1764695b7",
                "6976b8bafb8d6fe1764695b8",
                "6976b8bafb8d6fe1764695b9",
                "6976b8bafb8d6fe1764695ba",
                "6976b8bafb8d6fe1764695bb",
                "6976b8bafb8d6fe1764695bc",
                "6976b8bafb8d6fe1764695bd",
                "6976b8bafb8d6fe1764695be",
                "6976b8bafb8d6fe1764695bf",
                "6976b8bafb8d6fe1764695c0",
                "6976b8bafb8d6fe1764695c1",
                "6976b8bafb8d6fe1764695c2",
                "6976b8bafb8d6fe1764695c3",
            ],
            vote_result_list=[],
        )

        payload = DiscussionRequestPayload(
            event_id=event.event_id,
            event_type=EventType.DISCUSSION_REQUEST.value,
            payload=data,
        )

        await self._discussion_request_publisher.publish(
            headers=incoming_headers, 
            message=payload, 
            key=raw_key
        )
        print(f"Service: Published ai discussion request for key {display_key}")

    # 이벤트 타입 수정 필요
    async def publish_receipt_ocr_response(self, event, message: KafkaMessage):
        pass

    async def publish_ai_discussion_response(
        self,
        event_id: int,
        key: bytes,
        data: DiscussionResponseData,
    ):
        payload = DiscussionResponsePayload(
            event_id=event_id,
            event_type=EventType.DISCUSSION_RESPONSE.value,
            payload=data,
        )
        await self._discussion_response_publisher.publish(message=payload, key=key)
        print(
            f"Service: Published discussion response for key {key.decode('utf-8') if key else 'None'}"
        )

    # 에러 핸들러(아마 사용안할듯)
    def error_handler(self):
        @self.middleware.add_handler(Exception)
        async def validation_exception_handler(
            exc: Exception, message=Context()
        ) -> None:
            raw_msg = getattr(message, "raw_message", message)
            error_topic = getattr(raw_msg, "topic", "unknown")
            event_type = None

            match error_topic:
                case TopicType.RECOMMENDATION_REQUEST.value:
                    event_type = EventType.RECOMMENDATION_RESPONSE.value
                case TopicType.USER_PERSONA_UPDATE.value:
                    event_type = EventType.USER_PERSONA_UPDATE.value

            print(exc)
            print(f"error-topic : {error_topic}")
            print(f"publish-event-type : {event_type}")
            print(f"key : {getattr(raw_msg, 'key', None)}")
            print(f"value : {getattr(raw_msg, 'value', None)}")

    #  토픽 전달
    def get_recommendation_request_topic(self):
        return TopicType.RECOMMENDATION_REQUEST.value

    def get_recommendation_refresh_request_topic(self):
        return TopicType.RECOMMENDATION_REFRESH_REQUEST.value

    def get_restaurant_confirmed_topic(self):
        return TopicType.RESTAURANT_CONFIRMED.value

    def get_user_persona_update_topic(self):
        return TopicType.USER_PERSONA_UPDATE.value

    def get_receipt_ocr_request_topic(self):
        return TopicType.RECEIPT_OCR_REQUEST.value

    def get_ai_discussion_response_topic(self):
        return TopicType.DISCUSSION_RESPONSE.value

    def get_ai_discussion_request_topic(self):
        return TopicType.DISCUSSION_REQUEST.value
