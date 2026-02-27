import pytest
import os

# 테스트 실행 시 필수 환경 변수가 없으면 Pydantic ValidationError가 발생하므로 가짜 값 설정
def set_test_env():
    envs = {
        "MONGODB_URI": "mongodb://localhost:27017",
        "GOOGLE_API_KEY": "fake",
        "OPENAI_API_KEY": "fake",
        "LANGFUSE_SECRET_KEY": "fake",
        "LANGFUSE_PUBLIC_KEY": "fake",
        "LANGFUSE_BASE_URL": "http://localhost"
    }
    for key, value in envs.items():
        if key not in os.environ:
            os.environ[key] = value

set_test_env()
import asyncio

@pytest.fixture(scope="function")
async def db_manager():
    """
    각 테스트마다 새로운 DBManager를 생성하여 이벤트 루프 불일치 문제를 방지합니다.
    """
    from shared.database.db_manager import DBManager
    test_db_name = "damo"
    manager = DBManager(db_name=test_db_name)
    
    yield manager
    
    # 테스트 종료 시 클라이언트 닫기
    manager.client.close()