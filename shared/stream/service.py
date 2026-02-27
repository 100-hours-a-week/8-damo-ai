from faststream import ExceptionMiddleware, Context
from typing import Awaitable, Callable
from faststream.kafka import KafkaBroker, KafkaMessage
from aiokafka import ConsumerRecord
import dataclasses

from shared.schemas.stream_schema import (
    RecommendationRequestPayload,
    RecommendationResponseData,
    RecommendationResponsePayload,
<<<<<<< HEAD
    RecommendationStreamingPayload,
    RecommendationStreamingPayload,
    DiscussionRequestPayload,
    DiscussionResponseData,
    DiscussionResponseData,
    DiscussionResponsePayload,
    RecommendationStreamingData,
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

=======
    DiscussionRequestPayload,
    DiscussionResponsePayload,
    RecommendationStreamingData,
    EventType,
    TopicType
)
from shared.utils.config import get_settings

# 커스텀 파서
async def safe_header_parser(
    msg: ConsumerRecord, 
    original_parser: Callable[[ConsumerRecord], Awaitable[KafkaMessage]]
) -> KafkaMessage:
    safe_headers = []
    
>>>>>>> 0ce083c8830e6ce357a210212026081dd451b280
    # Kafka 원본 메시지(ConsumerRecord)에 헤더가 존재하는지 확인
    if msg.headers:
        for key, value in msg.headers:
            if key == "elasticapmtraceparent":
<<<<<<< HEAD
                continue  # (여기 아래 로직 안타고 다음 헤더로 넘어감)
            if isinstance(value, bytes):
                safe_value = value.decode("utf-8", errors="ignore").encode("utf-8")
                safe_headers.append((key, safe_value))
            else:
                safe_headers.append((key, value))

=======
                continue # (여기 아래 로직 안타고 다음 헤더로 넘어감)
            if isinstance(value, bytes):
                safe_value = value.decode('utf-8', errors='ignore').encode('utf-8')
                safe_headers.append((key, safe_value))
            else:
                safe_headers.append((key, value))
    
>>>>>>> 0ce083c8830e6ce357a210212026081dd451b280
    # ConsumerRecord는 namedtuple이므로 _replace를 사용해 헤더만 안전한 값으로 교체합니다.
    safe_msg = dataclasses.replace(msg, headers=tuple(safe_headers))
    return await original_parser(safe_msg)


class KafkaService:
    """
    카프카 연결을 위한 추상화 클래스
    """
<<<<<<< HEAD

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
        self._discussion_response_publisher = self.broker.publisher(
            TopicType.DISCUSSION_RESPONSE.value
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
=======
    def __init__(self):
        self.settings = get_settings()  
        self.middleware = ExceptionMiddleware()
        self.broker = KafkaBroker(
            self.settings.KAFKA_BOOTSTRAP_SERVERS, 
            middlewares=[self.middleware], 
            parser=safe_header_parser,
            client_id=self.settings.KAFKA_CLIENT_ID
        )
        self._recommendation_response_publisher = self.broker.publisher(TopicType.RECOMMENDATION_RESPONSE.value)
        self._recommendation_streaming_publisher = self.broker.publisher(TopicType.RECOMMENDATION_STREAMING.value)
        self.error_handler()

    async def publish_recommendation_response(self, event: RecommendationRequestPayload, message: KafkaMessage, data: RecommendationResponseData):
        resp_data = RecommendationResponsePayload(
            event_id=event.event_id,
            event_type=EventType.RECOMMENDATION_RESPONSE.value,
            payload=data
>>>>>>> 0ce083c8830e6ce357a210212026081dd451b280
        )

        incoming_headers = dict(message.headers) if message.headers else {}

        await self._recommendation_response_publisher.publish(
<<<<<<< HEAD
            headers=incoming_headers, message=resp_data, key=message.raw_message.key
        )
        print(
            f"Service: Published recommendation response for key {message.raw_message.key.decode('utf-8') if message.raw_message.key else 'None'}"
        )

    async def publish_recommendation_streaming(self, data: RecommendationStreamingData):
        await self._recommendation_streaming_publisher.publish(
            message=data, key=f"{data.dining_id}-{data.user_id}".encode("utf-8")
        )
        print(
            f"Service: Published recommendation streaming for key {data.dining_id}-{data.user_id}"
        )
=======
            headers=incoming_headers,
            message=resp_data,
            key=message.raw_message.key
        )
        print(f"Service: Published recommendation response for key {message.raw_message.key.decode('utf-8') if message.raw_message.key else 'None'}")

    async def publish_recommendation_streaming(self, data: RecommendationStreamingData):
        await self._recommendation_streaming_publisher.publish(
            message=data,
            key=f"{data.dining_id}-{data.user_id}".encode("utf-8")
        )
        print(f"Service: Published recommendation streaming for key {data.dining_id}-{data.user_id}")
>>>>>>> 0ce083c8830e6ce357a210212026081dd451b280

    # 이벤트 타입 수정 필요
    async def publish_receipt_ocr_response(self, event, message: KafkaMessage):
        pass

<<<<<<< HEAD
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
=======
    async def publish_ai_discussion_response(self, event, message: KafkaMessage):
        pass
>>>>>>> 0ce083c8830e6ce357a210212026081dd451b280

    # 에러 핸들러(아마 사용안할듯)
    def error_handler(self):
        @self.middleware.add_handler(Exception)
<<<<<<< HEAD
        async def validation_exception_handler(
            exc: Exception, message=Context()
        ) -> None:
=======
        async def validation_exception_handler(exc: Exception, message = Context()) -> None:
>>>>>>> 0ce083c8830e6ce357a210212026081dd451b280
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
<<<<<<< HEAD

    def get_ai_discussion_request_topic(self):
        return TopicType.DISCUSSION_REQUEST.value
=======
    
    def get_ai_discussion_request_topic(self):
        return TopicType.DISCUSSION_REQUEST.value
        
>>>>>>> 0ce083c8830e6ce357a210212026081dd451b280
