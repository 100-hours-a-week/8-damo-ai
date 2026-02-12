import pytest
from httpx import AsyncClient, ASGITransport
from services.core_service.app.main import app

@pytest.fixture
def anyio_backend():
    return 'asyncio'

# 공통 페이로드 정의
UPDATE_PERSONA_PAYLOAD = {
    "userData": {
        "id": 123456789,
        "nickname": "DAMO_TEST",
        "gender": "MALE",
        "ageGroup": "TWENTIES",
        "allergies": ["PEANUT", "MILK"],
        "likeFoodCategoriesId": ["KOREAN", "CHINESE"],
        "categoriesId": ["KOREAN", "CHINESE", "JAPANESE"],
        "otherCharacteristics": "매운 것을 좋아함"
    },
    "reviewData": [
        {
            "restaurantId": "rest123",
            "userId": 123456789,
            "rating": 5,
            "comment": "맛있어요"
        }
    ]
}

RESTAURANT_FIX_PAYLOAD = {
    "diningData": {
        "diningId": 276856973458919424,
        "groupsId": 678,
        "diningDate": "2025-01-29T15:00:00",
        "budget": 100000,
        "x": "127.1111",
        "y": "37.3947"
    },
    "restaurantId": "69783c8e8f56cf41f4e93106",
    "voteResultList": [
        {
            "restaurantId": "rest123",
            "likeCount": 5,
            "dislikeCount": 0,
            "likedUserIds": [123456789],
            "dislikedUserIds": []
        }
    ]
}

@pytest.mark.asyncio
async def test_health_check():
    """헬스 체크 확인"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "core_service"}

@pytest.mark.asyncio
async def test_update_persona():
    """페르소나 업데이트 확인"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/persona", json=UPDATE_PERSONA_PAYLOAD)
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["userId"] == 123456789

@pytest.mark.asyncio
async def test_restaurant_fix():
    """식당 확정 확인"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/restaurant_fix", json=RESTAURANT_FIX_PAYLOAD)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    assert res_json["restaurantId"] == RESTAURANT_FIX_PAYLOAD["restaurantId"] 
