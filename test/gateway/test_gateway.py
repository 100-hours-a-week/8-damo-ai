"""Gateway 핸들러 단위 테스트.

TestKafkaBroker 대신 핸들러를 직접 호출해 mock으로 검증한다.
노드 단위 로직은 test/services/recommendation/에서 별도 테스트.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call


def _make_dining_data_dict(**kwargs) -> dict:
    return {
        "dining_id": kwargs.get("dining_id", 1),
        "groups_id": 1,
        "dining_date": datetime(2025, 6, 1),
        "budget": 50000,
        "x": kwargs.get("x", "127.0"),
        "y": "37.0",
    }


def _make_event(dining_id: int = 1) -> MagicMock:
    event = MagicMock()
    event.event_id = 1
    event.payload.dining_data.dining_id = dining_id
    event.payload.dining_data.budget = 50000
    event.payload.dining_data.dining_date = datetime(2025, 6, 1)
    event.payload.user_ids = [1, 2]
    return event


def _make_final_selection() -> list:
    return [
        {"restaurant_id": "r1", "place_name": "식당A", "reason": "분위기 좋음"},
        {"restaurant_id": "r2", "place_name": "식당B", "reason": "가성비 좋음"},
    ]


@pytest.fixture(autouse=True)
def mock_service():
    """KafkaService 전체를 mock — 모듈 임포트 시 Kafka 연결 방지."""
    with patch("gateway.main.service") as svc:
        svc.publish_recommendation_response = AsyncMock()
        svc.publish_recommendation_streaming = AsyncMock()
        svc.get_recommendation_request_topic.return_value = "recommendation-request"
        svc.get_recommendation_refresh_request_topic.return_value = "recommendation-refresh-request"
        yield svc


class TestHandleRecommendation:
    @pytest.mark.asyncio
    async def test_calls_recommendation_task_with_on_persona_speak(self, mock_service):
        task_result = {
            "dining_id": 1,
            "final_selection": _make_final_selection(),
        }

        mock_db = MagicMock()
        mock_db.save_dining_session = AsyncMock(return_value={"currentPhase": 1})
        mock_db.set_collection = MagicMock()
        mock_db.update_phase_count = AsyncMock(return_value={"currentPhase": 1})

        with patch("gateway.main.recommendation_task", new_callable=AsyncMock, return_value=task_result) as mock_task, \
             patch("gateway.main.DBManager", return_value=mock_db):

            from gateway.main import handle_recommendation
            event = _make_event()
            mock_logger = MagicMock()
            mock_message = MagicMock()
            mock_message.correlation_id = "test-cid"

            await handle_recommendation(event, mock_logger, mock_message)

        mock_task.assert_called_once()
        _, kwargs = mock_task.call_args
        assert kwargs["on_persona_speak"] is not None
        assert callable(kwargs["on_persona_speak"])

    @pytest.mark.asyncio
    async def test_publishes_response_with_final_selection(self, mock_service):
        task_result = {
            "dining_id": 1,
            "final_selection": _make_final_selection(),
        }

        mock_db = MagicMock()
        mock_db.save_dining_session = AsyncMock(return_value={"currentPhase": 1})
        mock_db.set_collection = MagicMock()
        mock_db.update_phase_count = AsyncMock(return_value={"currentPhase": 1})

        with patch("gateway.main.recommendation_task", new_callable=AsyncMock, return_value=task_result), \
             patch("gateway.main.DBManager", return_value=mock_db):

            from gateway.main import handle_recommendation
            event = _make_event()
            mock_logger = MagicMock()
            mock_message = MagicMock()

            await handle_recommendation(event, mock_logger, mock_message)

        mock_service.publish_recommendation_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_persona_speak_publishes_streaming(self, mock_service):
        """on_persona_speak 콜백이 recommendation-streaming을 발행하는지 확인."""
        captured_callback = None

        async def capture_task(body, cid, log_type, on_persona_speak=None):
            nonlocal captured_callback
            captured_callback = on_persona_speak
            return {"dining_id": 1, "final_selection": []}

        mock_db = MagicMock()
        mock_db.save_dining_session = AsyncMock(return_value={"currentPhase": 1})
        mock_db.set_collection = MagicMock()
        mock_db.update_phase_count = AsyncMock(return_value={"currentPhase": 1})

        with patch("gateway.main.recommendation_task", side_effect=capture_task), \
             patch("gateway.main.DBManager", return_value=mock_db):

            from gateway.main import handle_recommendation
            event = _make_event()
            await handle_recommendation(event, MagicMock(), MagicMock())

        assert captured_callback is not None
        # 콜백 실제 호출
        await captured_callback({"user_id": 1, "content": "이 식당 좋아요!"})
        mock_service.publish_recommendation_streaming.assert_called_once()


class TestHandleRecommendationRefresh:
    @pytest.mark.asyncio
    async def test_calls_recommendation_task_refresh(self, mock_service):
        task_result = {
            "dining_id": 1,
            "final_selection": _make_final_selection(),
        }

        mock_db = MagicMock()
        mock_db.save_dining_session = AsyncMock(return_value={"currentPhase": 2})
        mock_db.set_collection = MagicMock()

        with patch("gateway.main.recommendation_task", new_callable=AsyncMock, return_value=task_result) as mock_task, \
             patch("gateway.main.DBManager", return_value=mock_db):

            from gateway.main import handle_recommendation_refresh
            event = _make_event()
            mock_message = MagicMock()

            await handle_recommendation_refresh(event, MagicMock(), mock_message)

        mock_task.assert_called_once()
        args, kwargs = mock_task.call_args
        assert args[2] == "refresh"
        assert callable(kwargs["on_persona_speak"])
