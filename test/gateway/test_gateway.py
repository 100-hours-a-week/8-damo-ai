import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from faststream.kafka import TestKafkaBroker
from gateway.main import broker
from shared.schemas.stream_schema import (
    RecommendationRequestPayload,
    EventType,
    DiningData,
    RecommendationRequestData
)
from datetime import datetime

@pytest.mark.asyncio
async def test_handle_recommendation():
    # 💡 핵심: 외부 의존성을 모두 Mock 처리하여 실제 DB/API 호출을 막음
    with patch("gateway.main.RunPodClient") as mock_runpod, \
         patch("gateway.main.DBManager") as mock_db, \
         patch("gateway.main.recommendation_task") as mock_task:
        
        # 가짜 응답 설정
        # health_check가 비동기 함수인 경우 AsyncMock 사용
        mock_runpod_instance = mock_runpod.return_value
        mock_runpod_instance.health_check = AsyncMock(return_value=True)
        
        mock_task.return_value = {
            "filtered_restaurant": [{"_id": "69783c8e8f56cf41f4e93109"}],
            "iteration_count": 1,
            "needs_discussion": True
        }

        # 테스트용 데이터 준비
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

        async with TestKafkaBroker(broker) as br:
            await br.publish(test_payload, topic="recommendation-request")
            
            # 핸들러가 비동기로 실행되므로 잠시 대기하거나 호출 여부 확인
            # TestKafkaBroker는 publish 호출 시 구독 중인 핸들러를 실행함
            mock_task.assert_called()
