"""Gateway 테스트용 conftest.

gateway.main은 module-level에서 여러 외부 의존성을 초기화하므로,
import 전에 sys.modules에 stub을 주입한다.
"""
import importlib
import sys
from types import ModuleType
from unittest.mock import MagicMock, AsyncMock, patch


def _stub_missing_modules() -> None:
    """설치되지 않은 의존성만 stub으로 등록.

    부모 패키지(google, google.cloud 등)는 실제 import를 먼저 시도해서
    google.genai 등 다른 google 패키지가 깨지지 않도록 한다.
    """
    # 부모 네임스페이스는 실제 패키지를 우선 import
    for parent in ["google", "google.cloud", "google.oauth2"]:
        if parent not in sys.modules:
            try:
                importlib.import_module(parent)
            except ImportError:
                sys.modules[parent] = ModuleType(parent)

    # leaf 모듈만 stub 등록
    for name in ["google.cloud.vision", "google.cloud.vision_v1", "google.oauth2.service_account"]:
        if name not in sys.modules:
            sys.modules[name] = ModuleType(name)


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
