"""Gateway 테스트용 conftest.

gateway.main은 module-level에서 여러 외부 의존성을 초기화하므로,
import 전에 sys.modules에 stub을 주입한다.
"""
import sys
from types import ModuleType
from unittest.mock import MagicMock, AsyncMock, patch


def _stub_missing_modules() -> None:
    """로컬에 설치되지 않은 heavy 의존성 stub 처리."""
    stubs = [
        "google.cloud.vision",
        "google.cloud.vision_v1",
        "google.oauth2",
        "google.oauth2.service_account",
    ]
    for name in stubs:
        if name not in sys.modules:
            # 부모 패키지도 함께 등록
            parts = name.split(".")
            for i in range(1, len(parts) + 1):
                pkg = ".".join(parts[:i])
                if pkg not in sys.modules:
                    sys.modules[pkg] = ModuleType(pkg)


def _import_gateway_main_with_mock() -> None:
    """KafkaService를 mock한 상태로 gateway.main을 import."""
    if "gateway.main" in sys.modules:
        return

    _stub_missing_modules()

    mock_broker = MagicMock()
    mock_broker.subscriber = lambda *a, **kw: (lambda f: f)

    mock_service = MagicMock()
    mock_service.broker = mock_broker
    mock_service.get_recommendation_request_topic.return_value = "recommendation-request"
    mock_service.get_recommendation_refresh_request_topic.return_value = "recommendation-refresh-request"
    mock_service.get_restaurant_confirmed_topic.return_value = "restaurant-confirmed"
    mock_service.get_user_persona_update_topic.return_value = "user-persona-update"
    mock_service.get_receipt_ocr_request_topic.return_value = "receipt-ocr-request"
    mock_service.publish_recommendation_response = AsyncMock()
    mock_service.publish_recommendation_streaming = AsyncMock()

    with patch("shared.stream.service.KafkaService", return_value=mock_service):
        import gateway.main  # noqa: F401


_import_gateway_main_with_mock()
