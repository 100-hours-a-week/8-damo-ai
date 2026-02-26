from faststream import FastStream, ExceptionMiddleware, Context
from faststream.kafka import KafkaBroker

from shared.schemas.stream_schema import (
    RecommendationRequestPayload,
    RecommendationResponseData,
    RecommendationResponsePayload,
    ConsensusDialogueData,
    ConsensusDialoguePayload,
    ConsensusResultData,
    ConsensusResultPayload,
    EventType,
    TopicType,
)
from shared.utils.config import get_settings


class KafkaService:
    """
    카프카 연결을 위한 추상화 클래스
    """

    def __init__(self):
        self.settings = get_settings()
        self.middleware = ExceptionMiddleware()
        self.broker = KafkaBroker(
            self.settings.KAFKA_BOOTSTRAP_SERVERS, middlewares=[self.middleware]
        )
        self._recommendation_response_publisher = self.broker.publisher(
            TopicType.RECOMMENDATION_RESPONSE.value
        )
        self._recommendation_streaming_publisher = self.broker.publisher(
            TopicType.RECOMMENDATION_STREAMING.value
        )
        self._recommendation_response_publisher = self.broker.publisher(
            self.settings.KAFKA_RECOMMENDATION_RESPONSE_TOPIC
        )
        self._recommendation_streaming_publisher = self.broker.publisher(
            self.settings.KAFKA_RECOMMENDATION_STREAMING_TOPIC
        )
        self._consensus_dialogue_publisher = self.broker.publisher(
            self.settings.KAFKA_CONSENSUS_DIALOGUE_TOPIC
        )
        self._consensus_result_publisher = self.broker.publisher(
            self.settings.KAFKA_CONSENSUS_RESULT_TOPIC
        )
        self.error_handler()

    async def publish_recommendation_response(
        self,
        event: RecommendationRequestPayload,
        key: bytes,
        data: RecommendationResponseData,
    ):
        resp_data = RecommendationResponsePayload(
            event_id=event.event_id,
            event_type=EventType.RECOMMENDATION_RESPONSE.value,
            payload=data,
        )

        await self._recommendation_response_publisher.publish(
            message=resp_data, key=key
        )
        print(
            f"Service: Published recommendation response for key {key.decode('utf-8') if key else 'None'}"
        )

    async def publish_recommendation_streaming(self, key: bytes, data: dict[str, str]):
        await self._recommendation_streaming_publisher.publish(message=data, key=key)
        print(
            f"Service: Published recommendation streaming for key {key.decode('utf-8') if key else 'None'}"
        )

    # 이벤트 타입 수정 필요
    async def publish_receipt_ocr_response(self, event, key: bytes):
        pass

    async def publish_consensus_dialogue(
        self, event_id: int, key: bytes, data: ConsensusDialogueData
    ) -> None:
        payload = ConsensusDialoguePayload(
            event_id=event_id,
            event_type=EventType.CONSENSUS_DIALOGUE.value,
            payload=data,
        )
        await self._consensus_dialogue_publisher.publish(
            message=payload,
            key=key,
        )
        print(
            f"Service: Published consensus dialogue for key {key.decode('utf-8') if key else 'None'}"
        )

    async def publish_consensus_result(
        self, event_id: int, key: bytes, data: ConsensusResultData
    ) -> None:
        payload = ConsensusResultPayload(
            event_id=event_id,
            event_type=EventType.CONSENSUS_RESULT.value,
            payload=data,
        )
        await self._consensus_result_publisher.publish(
            message=payload,
            key=key,
        )
        print(
            f"Service: Published consensus result for key {key.decode('utf-8') if key else 'None'}"
        )

    # 에러 핸들러(아마 사용안할듯)
    def error_handler(self):
        @self.middleware.add_handler(Exception)
        async def validation_exception_handler(
            exc: Exception, message=Context()
        ) -> None:
            error_topic = message.raw_message.topic
            event_type = None

            match message.raw_message.topic:
                case TopicType.RECOMMENDATION_REQUEST.value:
                    event_type = EventType.RECOMMENDATION_RESPONSE.value
                case TopicType.PERSONA_REQUEST.value:
                    event_type = EventType.PERSONA_RESPONSE.value
                case TopicType.CONSENSUS_REQUEST.value:
                    event_type = EventType.CONSENSUS_RESULT.value

            print(exc)
            print(f"error-topic : {error_topic}")
            print(f"publish-event-type : {event_type}")
            print(f"key : {message.raw_message.key}")
            print(f"value : {message.raw_message.value}")

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

    def get_persona_request_topic(self) -> str:
        return self.settings.KAFKA_PERSONA_REQUEST_TOPIC

    def get_consensus_request_topic(self) -> str:
        return self.settings.KAFKA_CONSENSUS_REQUEST_TOPIC
