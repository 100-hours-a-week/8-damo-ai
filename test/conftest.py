import pytest
from dotenv import load_dotenv

load_dotenv()

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