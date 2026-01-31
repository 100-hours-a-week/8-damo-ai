import pytest
from src.core.config import settings
from pymongo import MongoClient

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

    # 테스트 종료 후 원래 설정으로 원복
    settings.DB_NAME = original_db_name


@pytest.fixture(scope="function", autouse=True)
def clean_db():
    """
    테스트 간 데이터 간섭을 방지하고 실제 DB 오염을 막습니다.
    동기/비동기 테스트 호환성을 위해 Pymongo(동기 드라이버)를 사용합니다.
    """
    yield  # 테스트 함수 실행

    # 동기 방식으로 DB 삭제
    client = MongoClient(settings.MONGODB_URI)
    client.drop_database(TEST_DB_NAME)
    client.close()


@pytest.fixture(scope="function", autouse=True)
def seed_restaurants(clean_db):
    """
    테스트용 식당 데이터를 DB에 주입합니다.
    clean_db가 먼저 실행되어 DB를 비운 후 실행됩니다.
    """
    client = MongoClient(settings.MONGODB_URI)
    db = client[TEST_DB_NAME]
    collection = db["restaurants"]

    # 1. 지리적 인덱스 생성 (필수)
    collection.create_index([("location", "2dsphere")])

    # 2. 샘플 데이터 삽입
    # 테스트 요청 좌표: [127.1111, 37.3947]
    sample_restaurants = [
        {
            "id": "rest_1",
            "name": "Test Restaurant 1",
            "category": "KOREAN",
            "location": {"type": "Point", "coordinates": [127.1111, 37.3947]},
            "score": 4.5,
            "description": "맛있는 한식",
            "menus": [{"title": "Kimchi Stew", "price": 10000}],
            "images": [],
        },
        {
            "id": "rest_2",
            "name": "Test Restaurant 2",
            "category": "WESTERN",
            "location": {"type": "Point", "coordinates": [127.1112, 37.3948]},
            "score": 4.0,
            "description": "Not Bad Western",
            "menus": [{"title": "Pasta", "price": 15000}],
            "images": [],
        },
    ]

    collection.insert_many(sample_restaurants)
    client.close()
