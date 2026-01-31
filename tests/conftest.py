import pytest
import asyncio
from src.core.config import settings
from src.shared.database import get_client

# 테스트용 DB 이름 설정
TEST_DB_NAME = "damo_test_db"


@pytest.fixture(scope="session", autouse=True)
def override_db_settings():
    """
    전체 테스트 세션 동안 DB 이름을 테스트용 DB로 변경합니다.
    """
    original_db_name = settings.DB_NAME
    settings.DB_NAME = TEST_DB_NAME

    yield

    # 테스트 종료 후 원래 설정으로 원복 (사실 프로세스 종료되므로 필수는 아님)
    settings.DB_NAME = original_db_name


@pytest.fixture(scope="function", autouse=True)
async def clean_db():
    """
    매 테스트 함수 실행 후 테스트 DB를 삭제(Drop)하여
    테스트 간 데이터 간섭을 방지하고 실제 DB 오염을 막습니다.
    """
    yield  # 테스트 함수 실행

    client = get_client()
    await client.drop_database(TEST_DB_NAME)
