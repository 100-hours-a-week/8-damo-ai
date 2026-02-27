import asyncio
from faststream import FastStream, Context
from shared.stream.service import KafkaService
from shared.schemas.stream_schema import (
    RecommendationRequestPayload, 
    RecommendationResponseData,
    RecommendedItem,
    UserPersonaUpdatePayload,
    DiscussionResponsePayload,
    DiscussionRequestPayload
)
from shared.utils.config import get_settings
import requests

settings = get_settings()
service = KafkaService()
broker = service.broker
app = FastStream(broker)

# 추천 요청
@broker.subscriber(service.get_recommendation_request_topic(), group_id=settings.KAFKA_GROUP_ID)
async def handle_recommendation(event: RecommendationRequestPayload, message = Context()):
    print("get recommendation request")

    # def _send_background_request():
    #     # TODO: 실제 요청할 URL 및 데이터로 수정하세요
    #     try:
    #         response = requests.post("http://example.com/api", json={"test": "data"})
    #         print(f"Background request success: {response.status_code}")
    #     except Exception as e:
    #         print(f"Background request failed: {e}")
    
    # asyncio.create_task(asyncio.to_thread(_send_background_request))

    await service.publish_ai_discussion_request(event, message)


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

# @broker.subscriber(service.get_ai_discussion_request_topic(), group_id=settings.KAFKA_GROUP_ID)
# async def handle_discussion_request(event: DiscussionRequestPayload, message = Context()):
#     pass

@broker.subscriber(service.get_ai_discussion_response_topic(), group_id=settings.KAFKA_GROUP_ID)
async def handle_discussion_response(event: DiscussionResponsePayload, message = Context()):
    # DiscussionResponseData를 RecommendationResponseData 형식으로 변환하여 유효성 에러 해결
    recommendation_data = RecommendationResponseData(
        dining_id=event.payload.dining_id,
        recommendation_count=len(event.payload.final_restaurant_ids),
        recommended_items=[
            RecommendedItem(
                restaurant_id=item.restaurant_id,
                reasoning_description=item.summary
            ) for item in event.payload.final_restaurant_ids
        ]
    )
    await service.publish_recommendation_response(event, message, recommendation_data)

# 메인 함수
async def main():
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())