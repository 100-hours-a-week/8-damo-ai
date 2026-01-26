from fastapi import APIRouter
from fastapi.responses import JSONResponse
from src.features.recommendation.models.schemas.user import UserDataRequest, UserDataResponse
from src.features.recommendation.models.schemas.recommendation import RecommendationRequest, RecommendationResponse, AnalyzeRefreshRequest, RecommendedItem
from src.features.recommendation.graphs.update_persona_db import update_persona_db_v1
from src.features.recommendation.graphs.recommendations import recommendations_v1

router = APIRouter()

MOCK_DEV_ITEMS = [
    RecommendedItem(
        restaurant_id="6976b54010e1fa815903d4ce",
        restaurant_name="도치피자 고기리점",
        reasoning_description="사용자의 알레르기 수칙을 준수하며 평점이 높습니다."
    ),
    RecommendedItem(
        restaurant_id="6976b57f10e1fa815903d4cf",
        restaurant_name="우마주 판교대장점",
        reasoning_description="새로운 분위기의 식당으로 재추천되었습니다."
    ),
    RecommendedItem(
        restaurant_id="6976b58610e1fa815903d4d0",
        restaurant_name="마이페이보릿네이버",
        reasoning_description="가격이 저렴하며 리뷰가 많습니다."
    ),
    RecommendedItem(
        restaurant_id="6976b8b9fb8d6fe1764695b6",
        restaurant_name="BHC치킨 판교대장점",
        reasoning_description="특별한 메뉴가 있는 식당으로 추천되었습니다."
    ),
    RecommendedItem(
        restaurant_id="6976b8bafb8d6fe1764695b7",
        restaurant_name="우심 판교점",
        reasoning_description="가족과 함께 즐길 수 있는 식당으로 추천되었습니다."
    )
]

@router.post("/update_persona_db", 
            summary="사용자 데이터로 Persona를 업데이트",
            response_model=UserDataResponse)
async def update_persona_db(user_data_request: UserDataRequest):
    """
    사용자 데이터로 Persona를 업데이트하는 API(회원가입시, 리뷰 작성시 호출)
    """
    if user_data_request.user_data is None or user_data_request.user_data == []:
        return JSONResponse(
            status_code=400, content={"success": False, "message": "data is empty or is not exists"}
        )
    
    target_user_id = user_data_request.user_data[0].id if user_data_request.user_data else 0

    result = await update_persona_db_v1(user_data_request)    

    return UserDataResponse(
        success=True,
        process_time=result.get("process_time", 0.0),
        user_id=target_user_id
    )

@router.post("/recommendations", 
            summary="식당 추천시 호출하는 API",
            response_model=RecommendationResponse)
async def recommendations(recommendation_request: RecommendationRequest):
    """
    식당 추천시 호출하는 API로 내부 그래프 처리 후 최종 5개의 식당 정보를 반환합니다.
    """
    if recommendation_request.dining_data is None:
        return JSONResponse(
            status_code=400, content={"success": False, "message": "diningData is required"}
        )
    
    if recommendation_request.user_data is None or recommendation_request.user_data == []:
        return JSONResponse(
            status_code=400, content={"success": False, "message": "userData is empty or is not exists"}
        )

    result = await recommendations_v1(recommendation_request, False, 0)
    
    return RecommendationResponse(
        success=True,
        process_time=result.get("process_time", 0.0),
        recommended_items=MOCK_DEV_ITEMS
    )

@router.post("/analyze_refresh", 
            summary="사용자가 재추천을 원할 경우 호출하는 API",
            response_model=RecommendationResponse)
async def analyze_refresh(recommendation_request: AnalyzeRefreshRequest):
    """
    식당 재추천시 호출하는 API로 내부 그래프 처리 후 최종 5개의 식당 정보를 반환합니다.
    """
    if recommendation_request.dining_data is None:
        return JSONResponse(
            status_code=400, content={"success": False, "message": "diningData is required"}
        )
    
    if recommendation_request.user_data is None or recommendation_request.user_data == []:
        return JSONResponse(
            status_code=400, content={"success": False, "message": "userData is empty or is not exists"}
        )

    result = await recommendations_v1(recommendation_request, True, recommendation_request.refresh_count)
    
    return RecommendationResponse(
        success=True,
        process_time=result.get("process_time", 0.0),
        recommended_items=MOCK_DEV_ITEMS
    )