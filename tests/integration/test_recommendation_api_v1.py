import sys
import os
# 프로젝트 루트 디렉토리를 sys.path에 추가하여 main을 찾을 수 있게 합니다.
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi.testclient import TestClient
from main import app
from datetime import datetime

client = TestClient(app)

def test_update_persona_db():
    """
    CI용 목업 테스트: Persona 업데이트 API 호출 테스트 (CamelCase JSON 통신)
    """
    # Spring 방식의 camelCase JSON 요청
    payload = {
        "userData": [
            {
                "id": 123456789,
                "email": "test@example.com",
                "nickname": "테스터",
                "gender": "MALE",
                "ageGroup": "TWENTIES",
                "isPushNotificationAllowed": True,
                "createdAt": "2024-01-26T10:00:00",
                "updatedAt": "2024-01-26T10:00:00",
                "allergies": ["MILK", "EGG"],
                "dislikes": ["SEAFOOD"]
            }
        ]
    }

    response = client.post("/ai/api/v1/update_persona_db", json=payload)

    assert response.status_code == 200
    data = response.json()
    # 응답도 camelCase로 오는지 확인
    assert data["success"] is True
    assert data["userId"] == 123456789
    assert "processTime" in data
    assert data["processTime"] < 10.0 # 10초 이내 검수

def test_health_check():
    """헬스 체크 엔드포인트 테스트"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_recommendations():
    """식당 추천 API 호출 테스트 (CamelCase JSON 통신)"""
    payload = {
        "diningData": {
            "id": 1,
            "groupsId": 10,
            "diningDate": "2024-02-01T19:00:00",
            "voteDueDate": "2024-01-31T23:59:59",
            "budget": 50000,
            "createdAt": "2024-01-20T10:00:00"
        },
        "userData": [
            {
                "id": 123456789,
                "email": "test@example.com",
                "nickname": "테스터",
                "gender": "MALE",
                "ageGroup": "TWENTIES"
            }
        ]
    }
    response = client.post("/ai/api/v1/recommendations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["processTime"] < 10.0 # 10초 이내 검수
    assert "recommendedItems" in data
    assert isinstance(data["recommendedItems"], list)
    assert len(data["recommendedItems"]) > 0
    
    # Pydantic 타입과 동일한지(필드 존재 여부) 검수
    first_item = data["recommendedItems"][0]
    assert "restaurantId" in first_item
    assert "restaurantName" in first_item
    assert "reasoningDescription" in first_item
    # assert first_item["restaurantName"] == "도치피자 고기리점"

def test_analyze_refresh():
    """재추천 API 호출 테스트 (CamelCase JSON 통신)"""
    payload = {
        "diningData": {
            "id": 1,
            "groupsId": 10,
            "diningDate": "2024-02-01T19:00:00",
            "voteDueDate": "2024-01-31T23:59:59",
            "budget": 50000,
            "createdAt": "2024-01-20T10:00:00"
        },
        "userData": [
            {
                "id": 123456789,
                "email": "test@example.com",
                "nickname": "테스터",
                "gender": "MALE",
                "ageGroup": "TWENTIES"
            }
        ],
        "refreshCount": 1
    }
    response = client.post("/ai/api/v1/analyze_refresh", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["processTime"] < 10.0 # 10초 이내 검수
    assert "recommendedItems" in data
    assert len(data["recommendedItems"]) > 0
    assert data["recommendedItems"][0]["restaurantName"] == "도치피자 고기리점"
