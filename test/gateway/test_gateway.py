import pytest
from faststream.kafka import TestKafkaBroker
from gateway.main import broker, handle_recommendation
from shared.schemas.stream_schema import (
    RecommendationRequestPayload,
    EventType,
    DiningData,
    RecommendationRequestData
)
from datetime import datetime

@pytest.mark.asyncio
async def test_handle_recommendation():
    # 1. TestKafkaBroker를 사용하여 실제 Kafka 없이 테스트 모드 진입
    async with TestKafkaBroker(broker) as br:
        # 2. 테스트용 데이터 준비
        test_payload = RecommendationRequestPayload(
            event_id=1,
            event_type=EventType.RECOMMENDATION_REQUEST,
            payload=RecommendationRequestData(
                dining_data=DiningData(
                    dining_id=1,
                    groups_id=1,
                    dining_date=datetime.now(),
                    budget=50000,
                    x="127.0",
                    y="37.0"
                ),
                user_ids=[1, 2, 3]
            )
        )

        # 3. 특정 토픽으로 메시지 발행 (main.py의 서비스 토픽 사용)
        # br.publish를 호출하면 @broker.subscriber가 달린 함수가 즉시 실행됩니다.
        await br.publish(
            test_payload, 
            topic="recommendation-request", # 실제 토픽 명 혹은 service.get_..._topic() 사용
            key=b"test-key"
        )
        
        # 4. (선택 사항) 핸들러 내의 부수 효과(DB 저장, 응답 발행 등)를 검증
        # 이 예시에서는 에러 없이 실행되는지만 확인합니다.
