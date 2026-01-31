import sys
import os
import random

# 프로젝트 루트 디렉토리를 sys.path에 추가하여 main을 찾을 수 있게 합니다.
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


from unittest.mock import AsyncMock, patch, MagicMock


@patch("src.recommendation.router.routes_v1.UsersRepository")
@patch(
    "src.recommendation.router.routes_v1.create_persona_description",
    new_callable=AsyncMock,
)
def test_update_persona_db(mock_create_persona, MockUsersRepo):
    """
    CI용 목업 테스트: Persona 업데이트 API 호출 테스트 (CamelCase JSON 통신)
    """
    # 1. create_persona_description Mock 설정
    mock_create_persona.return_value = "Mock Generated Persona Description"

    # 2. UsersRepository Mock 설정
    mock_repo_instance = MockUsersRepo.return_value

    # 저장 후 반환될 User 객체 Mock
    mock_saved_user = MagicMock()
    mock_saved_user.id = 123456789
    # save 메서드는 async이므로 AsyncMock 설정
    mock_repo_instance.save = AsyncMock(return_value=mock_saved_user)

    # Spring 방식의 camelCase JSON 요청
    payload = {
        "userData": {
            "id": 123456789,
            "nickname": "테스터",
            "gender": "MALE",
            "ageGroup": "TWENTIES",
            "allergies": ["MILK", "EGG"],
            "likeFoodCategoriesId": ["KOREAN", "JAPANESE"],
            "categoriesId": ["KOREAN"],
            "otherCharacteristics": "매운거 못먹음",
        },
        "reviewData": [],
    }

    # API 호출
    response = client.post("/ai/api/v1/update_persona_db", json=payload)

    # 응답 검증
    assert response.status_code == 200
    data = response.json()

    # 응답도 camelCase로 오는지 확인
    assert data["success"] is True
    assert data["userId"] == 123456789


def test_health_check():
    """헬스 체크 엔드포인트 테스트"""
    response = client.get("/ai/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_recommendations():
    """식당 추천 API 호출 테스트 (CamelCase JSON 통신)"""
    test_dining_id = random.randint(1, 1000000)
    payload = {
        "diningData": {
            "diningId": test_dining_id,
            "groupsId": 10,
            "diningDate": "2024-02-01T19:00:00",
            "budget": 50000,
            "x": "127.1111",  # Added required field
            "y": "37.3947",  # Added required field
        },
        "userIds": [1001, 1002, 1003],
    }
    response = client.post("/ai/api/v1/recommendations", json=payload)
    if response.status_code != 200:
        print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert "recommendedItems" in data
    assert "recommendationCount" in data
    assert isinstance(data["recommendedItems"], list)
    assert len(data["recommendedItems"]) > 0

    # Pydantic 타입과 동일한지(필드 존재 여부) 검수
    first_item = data["recommendedItems"][0]
    assert "restaurantId" in first_item
    assert "reasoningDescription" in first_item


def test_analyze_refresh():
    """재추천 API 호출 테스트 (CamelCase JSON 통신)"""
    test_dining_id = random.randint(1, 1000000)
    setup_payload = {
        "diningData": {
            "diningId": test_dining_id,
            "groupsId": 10,
            "diningDate": "2024-02-01T19:00:00",
            "budget": 50000,
            "x": "127.1111",  # Added required field
            "y": "37.3947",  # Added required field
        },
        "userIds": [1001, 1002, 1003],
    }
    client.post("/ai/api/v1/recommendations", json=setup_payload)

    payload = {
        "diningData": {
            "diningId": test_dining_id,
            "groupsId": 10,
            "diningDate": "2024-02-01T19:00:00",
            "budget": 50000,
            "x": "127.1111",  # Matches seed_restaurants location
            "y": "37.3947",  # Matches seed_restaurants location
        },
        "userIds": [1001, 1002, 1003],
        "voteResultList": [],
    }
    response = client.post("/ai/api/v1/analyze_refresh", json=payload)
    if response.status_code != 200:
        print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert "recommendedItems" in data
    assert len(data["recommendedItems"]) > 0


def test_restaurant_fix():
    """최종 식당 확정 API 호출 테스트"""
    test_id = random.randint(1, 1000000)  # 고유 ID 생성

    # 1. 사전 세션 생성 (Setup)
    setup_payload = {
        "diningData": {
            "diningId": test_id,
            "groupsId": 10,
            "diningDate": "2024-02-01T19:00:00",
            "budget": 50000,
            "x": "127.1111",  # Added required field
            "y": "37.3947",  # Added required field
        },
        "userIds": [1001, 1002, 1003],
    }
    setup_res = client.post("/ai/api/v1/recommendations", json=setup_payload)
    assert setup_res.status_code == 200
    setup_data = setup_res.json()
    real_restaurant_id = setup_data["recommendedItems"][0]["restaurantId"]

    # 2. 결과 확정 요청
    payload = {
        "diningData": setup_payload["diningData"],
        "restaurantId": real_restaurant_id,
        "voteResultList": [],
    }
    response = client.post("/ai/api/v1/restaurant_fix", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["restaurantId"] == real_restaurant_id
