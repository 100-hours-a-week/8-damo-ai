import asyncio
from faststream import Context, Logger
from faststream.asgi import AsgiFastStream
from shared.stream.service import KafkaService
from shared.database.db_manager import DBManager
# Kafka 페이로드
from shared.schemas.stream_schema import (
    RecommendationRequestPayload, 
    RecommendationRefreshRequestPayload,
    RecommendationResponseData,
    RecommendedItem,
    RestaurantConfirmedPayload,
    UserPersonaUpdatePayload,
    DiscussionResponsePayload,
    ReceiptOCRRequestPayload,
    DiscussionRequestData
)
# 기존 Graph 관련 State
from shared.schemas.user_data import UserData
from shared.schemas.update_persona_db_request import UpdatePersonaDBRequest

from shared.utils.config import get_settings

# ASGI 및 클라이언트 접속을 위한 모듈
from services.core_service.modules.web_connections import health_check, log_check
from services.core_service.modules.runpod_connections import RunPodClient

# 서브 그래프
from services.core_service.modules.persona.task import analyze_persona_task
from services.recommendation.task import recommendation_task
from services.recommendation.sub_graphs.fix import fix_task

from services.core_service.modules.ocr.service import GoogleVisionService

# ------------------------------------------------
# ------------------------------------------------
# 메인 앱 구동을 위한 라이브러리
# 이 하단부터는 실제 kafka와 소통하는 메시지 토픽과 추상화된 response를 작성
settings = get_settings()
service = KafkaService()
broker = service.broker
app = AsgiFastStream(
    broker,
    asgi_routes=[
        ("/health_check", health_check),
        ("/log_check", log_check)
    ]
)
runpod = RunPodClient()
# ------------------------------------------------
# 회식 관련
# 1. 회식 추천
@broker.subscriber(service.get_recommendation_request_topic(), group_id=settings.KAFKA_GROUP_ID)
async def handle_recommendation(event: RecommendationRequestPayload, logger: Logger, message = Context()):
    logger.info("get recommendation request")
    # 백그라운드가 아닌 현재 흐름에서 에러를 체크하기 위해 await 사용
    try:
        is_healthy = await runpod.health_check()
        if not is_healthy:
            logger.error("RunPod is not healthy")
            raise Exception("RunPod is not healthy")
        correlation_id = str(getattr(message, "correlation_id", "unknown"))
        final_state = await recommendation_task(event.payload, correlation_id, "recommend")

        db = DBManager()
        await db.save_dining_session(final_state) 

        print("✅ request_waiting_final_state")
        raw_restaurants = final_state.get("filtered_restaurant", [])
        restaurant_ids = [str(res.get("_id")) for res in raw_restaurants if res.get("_id")]

        # 2. 데이터 조립하기
        discussion_data = DiscussionRequestData(
            dining_data=event.payload.dining_data,
            user_ids=event.payload.user_ids,
            filtered_restaurant=restaurant_ids,
            vote_result_list=[]
        )
        # 3. 토픽 발행
        await service.publish_ai_discussion_request(
            event_id=event.event_id,
            key=message.raw_message.key,
            headers=dict(message.headers),
            data=discussion_data
        )
    except Exception as e:
        logger.error(f"Error in handle_recommendation: {e}")
        raise e
# ------------------------------------------------
# 2. 회식 재추천
@broker.subscriber(service.get_recommendation_refresh_request_topic(), group_id=settings.KAFKA_GROUP_ID)
async def handle_recommendation_refresh(event: RecommendationRefreshRequestPayload, logger: Logger, message = Context()):
    logger.info("get recommendation refresh request")
    try:
        # 재추천 가능 여부 체크
        is_healthy = await runpod.health_check()
        if not is_healthy:
            logger.error("RunPod is not healthy")
            raise Exception("RunPod is not healthy")
        correlation_id = str(getattr(message, "correlation_id", "unknown"))
        final_state = await recommendation_task(event.payload, correlation_id, "refresh")

        db = DBManager()
        updated_session = await db.save_dining_session(final_state) 
        current_count = updated_session.get("currentPhase", 1) if updated_session else 1
        print("✅ refresh_waiting_final_state")

        print(final_state.get("status_message"))
        print("needs_discussion")
        print(final_state.get("needs_discussion"))

        if final_state.get("needs_discussion"):
            raw_restaurants = final_state.get("filtered_restaurant", [])
            restaurant_ids = [str(res.get("_id")) for res in raw_restaurants if res.get("_id")]

            # 2. 데이터 조립하기
            discussion_data = DiscussionRequestData(
                dining_data=event.payload.dining_data,
                user_ids=event.payload.user_ids,
                filtered_restaurant=restaurant_ids,
                vote_result_list=[]
            )
            # 3. 토픽 발행
            await service.publish_ai_discussion_request(
                event_id=event.event_id,
                key=message.raw_message.key,
                headers=dict(message.headers),
                data=discussion_data
            )
        else:
            raw_res = final_state.get("filtered_restaurant", [])
            items = [
                RecommendedItem(
                    restaurant_id=str(res.get("_id")),
                    reasoning_description="이전 추천 후보군에서 선별되었습니다."
                ) for res in raw_res if res.get("_id")
            ]
            response_data = RecommendationResponseData(
                dining_id=final_state["dining_id"],
                recommendation_count=current_count,
                recommended_items=items
            )
            await service.publish_recommendation_response(
                event=event,      # 통째로 전달
                message=message,  # 통째로 전달
                data=response_data
            )
        
    except Exception as e:
        logger.error(f"Critical error in recommendation handler: {e}")
        raise e
# ------------------------------------------------
# 3. AI 서버 응답 체크
@broker.subscriber(service.get_ai_discussion_response_topic(), group_id=settings.KAFKA_GROUP_ID)
async def handle_discussion_response(event: DiscussionResponsePayload, logger: Logger, message = Context()):
    logger.info(f"Received discussion response for dining: {event.payload.dining_id}")
    try:
        payload = event.payload
        
        # 1. DB에서 추천 차수(Phase) 1 증가시키기
        db = DBManager()
        db.set_collection("dining_sessions")
        updated_doc = await db.update_phase_count(
            filter_query={"diningId": payload.dining_id}, 
            field_name="currentPhase"
        )
        
        # 문서가 없는 경우를 대비한 기본값 1
        current_count = updated_doc.get("currentPhase", 1) if updated_doc else 1
        
        # 2. 추천 아이템 리스트 변환 (Summary -> ReasoningDescription)
        items = [
            RecommendedItem(
                restaurant_id=item.restaurant_id,
                reasoning_description=item.summary
            ) for item in payload.final_restaurant_ids
        ]
        
        # 3. BE로 보낼 최종 데이터 생성
        response_data = RecommendationResponseData(
            dining_id=payload.dining_id,
            recommendation_count=current_count,
            recommended_items=items
        )
        
        # 4. Kafka 발행
        await service.publish_recommendation_response(event, message, response_data)
        logger.info(f"Successfully published recommendation #{current_count}")

    except Exception as e:
        logger.error(f"Error in handle_discussion_response: {e}")
        raise e
# ------------------------------------------------
# 4. 장소 확정
@broker.subscriber(service.get_restaurant_confirmed_topic(), group_id=settings.KAFKA_GROUP_ID)
async def handle_restaurant_confirmed(event: RestaurantConfirmedPayload, logger: Logger, message = Context()):
    logger.info(f"Received restaurant confirmed for dining: {event.payload.dining_data.dining_id}")
    try:
        await fix_task(event)
    except Exception as e:
        logger.error(f"Error in handle_restaurant_confirmed: {e}")
        raise e
# ------------------------------------------------
# 5. 페르소나 업데이트
@broker.subscriber(service.get_user_persona_update_topic(), group_id=settings.KAFKA_GROUP_ID)
async def handle_persona_update(event: UserPersonaUpdatePayload, logger: Logger, message = Context()):
    logger.info("Starting persona update process")
    try:
        correlation_id = str(getattr(message, "correlation_id", "unknown"))
        payload = event.payload
        
        # UserPersonaUpdateData -> UserData 매핑 (필드명 및 타입 변환 보조)
        user_data = UserData(
            id=payload.user_id,
            nickname=payload.nickname,
            gender=payload.gender,
            age_group=payload.age_group,
            allergies=payload.allergies,
            like_food_categories_id=payload.like_foods,
            categories_id=payload.like_ingredients,
            other_characteristics=payload.other_characteristics or ""
        )
        
        # analyze_persona_task가 기대하는 UpdatePersonaDBRequest로 감싸서 전달
        db_request = UpdatePersonaDBRequest(
            user_data=user_data,
            review_data=[]  # 리뷰 정보가 없는 경우 빈 리스트로 초기화
        )
        
        await analyze_persona_task(db_request, logger, correlation_id)
    except Exception as e:
        logger.error(f"Critical error in persona update handler: {e}")
        raise e
# ------------------------------------------------
# 6. OCR 요청
@broker.subscriber(service.get_receipt_ocr_request_topic(), group_id=settings.KAFKA_GROUP_ID)
async def handle_receipt_ocr(event: ReceiptOCRRequestPayload, logger: Logger, message = Context()):
    logger.info("get receipt ocr request")
    try:
        payload = event.payload
        print(payload)
        google_service = GoogleVisionService()
        print(await google_service.check_client())

        # logger.info(payload)
        # await service.publish_receipt_ocr_response(payload, message)
    except Exception as e:
        logger.error(f"Critical error in receipt ocr handler: {e}")
        raise e
# ------------------------------------------------

@app.after_shutdown
async def cleanup():
    await runpod.close()

# 메인 함수
async def main():
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())