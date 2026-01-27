from fastapi import APIRouter
from fastapi.responses import JSONResponse
from src.recommendation.schemas.requests.user_request import UserDataRequest
from src.recommendation.schemas.responses.user_response import UserDataResponse
from src.recommendation.schemas.requests.recommendation_request import (
    RecommendationRequest,
    AnalyzeRefreshRequest,
)
from src.recommendation.schemas.responses.recommendation_response import (
    RecommendationResponse,
)
from src.recommendation.workflows.update_persona_db import update_persona_db_v1
from src.recommendation.workflows.recommendations import recommendations_v1
from src.recommendation.data.mock_items import MOCK_DEV_ITEMS

router = APIRouter()


@router.post(
    "/update_persona_db",
    summary="사용자 데이터로 Persona를 업데이트",
    response_model=UserDataResponse,
)
async def update_persona_db(user_data_request: UserDataRequest):
    """
    사용자 데이터로 Persona를 업데이트하는 API(회원가입시, 리뷰 작성시 호출)
    """
    if user_data_request.user_data is None:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "data is empty or is not exists"},
        )

    target_user_id = user_data_request.user_data.id

    return UserDataResponse(success=True, user_id=target_user_id)


@router.post(
    "/recommendations",
    summary="식당 추천시 호출하는 API",
    response_model=RecommendationResponse,
)
async def recommendations(recommendation_request: RecommendationRequest):
    """
    식당 추천시 호출하는 API로 내부 그래프 처리 후 최종 5개의 식당 정보를 반환합니다.
    """
    if recommendation_request.dining_data is None:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "diningData is required"},
        )

    if not recommendation_request.user_ids:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "user_ids is empty"},
        )

    result = await recommendations_v1(recommendation_request, False, 0)

    return RecommendationResponse(
        recommendation_count=result.get("recommendation_count", 0),
        recommended_items=MOCK_DEV_ITEMS,
    )


@router.post(
    "/analyze_refresh",
    summary="사용자가 재추천을 원할 경우 호출하는 API",
    response_model=RecommendationResponse,
)
async def analyze_refresh(recommendation_request: AnalyzeRefreshRequest):
    """
    식당 재추천시 호출하는 API로 내부 그래프 처리 후 최종 5개의 식당 정보를 반환합니다.
    """
    if recommendation_request.dining_data.dining_id is None:
        return JSONResponse(
            status_code=400,
            content={"message": "diningData.diningId is required"},
        )

    # analyze_refresh는 재추천이므로 is_refresh=True로 가정.
    # refresh_count나 투표 결과 처리는 graph 내부 로직에 위임.
    result = await recommendations_v1(recommendation_request, True, 1)

    return RecommendationResponse(
        recommendation_count=result.get("recommendation_count", 0),
        recommended_items=MOCK_DEV_ITEMS,
    )
