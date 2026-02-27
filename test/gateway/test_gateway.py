import pytest
import os
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

# 테스트 실행 시 필수 환경 변수가 없어도 에러가 나지 않도록 가짜 값 설정 (이미 환경 변수가 있으면 유지)
def set_fake_env():
    envs = {
        "MONGODB_URI": "mongodb://localhost:27017",
        "GOOGLE_API_KEY": "fake_key",
        "OPENAI_API_KEY": "fake_key",
        "LANGFUSE_SECRET_KEY": "fake_key",
        "LANGFUSE_PUBLIC_KEY": "fake_key",
        "LANGFUSE_BASE_URL": "http://localhost:3000",
        "RECOMMENDATION_URL": "http://recommendation:8000",
        "CORE_SERVICE_URL": "http://core_service:8000"
    }
    for key, value in envs.items():
        if key not in os.environ:
            os.environ[key] = value

set_fake_env()

from gateway.main import app

@pytest.fixture
def anyio_backend():
    return 'asyncio'

# 공통 페이로드 정의
UPDATE_PERSONA_PAYLOAD = {
    "userData": {
        "id": 123456789,
        "nickname": "맛있는녀석들",
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

RECOMMENDATIONS_PAYLOAD = {
    "diningData": {
        "diningId": 12345,
        "groupsId": 678,
        "diningDate": "2025-01-29T15:00:00",
        "budget": 100000,
        "x": "127.1111",
        "y": "37.3947"
    },
    "userIds": [123456789]
}

@pytest.mark.asyncio
async def test_root():
    """루트 엔드포인트 확인"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the API Gateway"}

@pytest.mark.asyncio
async def test_health_check():
    """헬스 체크 확인"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/ai/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "gateway"}

@pytest.mark.asyncio
async def test_update_persona_db_proxy():
    """update_persona_db 프록시 테스트"""
    mock_response_data = {
        "success": True,
        "userId": 123456789
    }
    
    with patch("shared.utils.client.ServiceClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response_data
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/ai/api/update_persona_db", json=UPDATE_PERSONA_PAYLOAD)
            
        assert response.status_code == 200
        assert response.json() == mock_response_data
        mock_post.assert_called_once()

@pytest.mark.asyncio
async def test_recommendations_proxy():
    """recommendations 프록시 테스트"""
    # RecommendationsResponse 스키마에 맞춘 모킹 데이터
    mock_response_data = {
        "recommendationCount": 1,
        "recommendedItems": []
    }
    
    with patch("shared.utils.client.ServiceClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response_data
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/ai/api/recommendations", json=RECOMMENDATIONS_PAYLOAD)
            
        assert response.status_code == 200
        assert response.json() == mock_response_data
        mock_post.assert_called_once()

@pytest.mark.asyncio
async def test_gateway_proxy_error():
    """상위 서비스 에러 시 502 응답 확인"""
    with patch("shared.utils.client.ServiceClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("Connection error")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/ai/api/update_persona_db", json=UPDATE_PERSONA_PAYLOAD)
            
        assert response.status_code == 502
        assert response.json()["detail"] == "Upstream Service Error"
