import asyncio
from faststream import FastStream, Context
from shared.stream.service import KafkaService
from shared.schemas.stream_schema import (
    RecommendationRequestPayload, 
    RecommendedItem,
    RecommendationResponseData,
    RecommendationRefreshRequestPayload,
    UserPersonaUpdatePayload,
    RecommendationStreamingData
)
from shared.utils.config import get_settings

settings = get_settings()
service = KafkaService()
broker = service.broker
app = FastStream(broker)

# 추천 요청
@broker.subscriber(service.get_recommendation_request_topic(), group_id=settings.KAFKA_GROUP_ID)
async def handle_recommendation(event: RecommendationRequestPayload, message = Context()):
    print("get recommendation request")
    await asyncio.sleep(1)

    # TODO: 실제 추천 로직 구현
    resp_data = RecommendationResponseData(
        dining_id=event.payload.dining_data.dining_id,
        recommendation_count=1,
        recommended_items=[
            RecommendedItem(
                restaurant_id="1",
                reasoning_description="test"
            )
        ]
    )

    # await service.publish_recommendation_response(event, message, resp_data)
    await service.publish_recommendation_streaming(RecommendationStreamingData(
        dining_id=1,
        user_id=1,
        content="test"
    ))

# 재추천 요청
@broker.subscriber(service.get_recommendation_refresh_request_topic(), group_id=settings.KAFKA_GROUP_ID)
async def handle_recommendation_refresh(event, message = Context()):
    print("get recommendation refresh request")
    print(event)

# 확정 요청
# 이벤트 타입 수정 필요
@broker.subscriber(service.get_restaurant_confirmed_topic(), group_id=settings.KAFKA_GROUP_ID)
async def handle_restaurant_confirmed(event, message = Context()):
    print("get restaurant confirmed request")
    print(event)

# 페르소나 요청
@broker.subscriber(service.get_user_persona_update_topic(), group_id=settings.KAFKA_GROUP_ID)
async def handle_persona(event: UserPersonaUpdatePayload, message = Context()):
    print("get persona request")
    print(event)
    
# OCR 요청
# 이벤트 타입 수정 필요
@broker.subscriber(service.get_receipt_ocr_request_topic(), group_id=settings.KAFKA_GROUP_ID)
async def handle_receipt_ocr(event, message = Context()):
    print("get receipt ocr request")
    print(event)

# 메인 함수
async def main():
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())