from fastapi import APIRouter
from fastapi.responses import JSONResponse
from src.recommendation.schemas.update_persona_db_request import UpdatePersonaDBRequest
from src.recommendation.schemas.update_persona_db_response import (
    UpdatePersonaDBResponse,
)
from src.recommendation.schemas.recommendations_request import RecommendationsRequest
from src.recommendation.schemas.recommendations_response import RecommendationsResponse
from src.recommendation.schemas.analyze_refresh_request import AnalyzeRefreshRequest
from src.recommendation.schemas.analyze_refresh_response import AnalyzeRefreshResponse
from src.recommendation.schemas.restaurant_fix_request import RestaurantFixRequest
from src.recommendation.schemas.restaurant_fix_response import RestaurantFixResponse
from src.recommendation.data.mock_items import (
    MOCK_RECOMMENDATIONS_RESPONSE,
    MOCK_ANALYZE_REFRESH_RESPONSE,
)

router = APIRouter()


@router.post(
    "/update_persona_db",
    summary="사용자 데이터로 Persona를 업데이트",
    response_model=UpdatePersonaDBResponse,
)
async def update_persona_db(request: UpdatePersonaDBRequest):
    """
    사용자 데이터로 Persona를 업데이트하는 API(회원가입시, 리뷰 작성시 호출)
    """
    if request.user_data is None:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "data is empty or is not exists"},
        )

    target_user_id = request.user_data.id

    return UpdatePersonaDBResponse(success=True, user_id=target_user_id)


@router.post(
    "/recommendations",
    summary="식당 추천시 호출하는 API",
    response_model=RecommendationsResponse,
)
async def recommendations(request: RecommendationsRequest):
    """
    식당 추천시 호출하는 API로 내부 그래프 처리 후 최종 5개의 식당 정보를 반환합니다.
    """
    if request.dining_data is None:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "diningData is required"},
        )

    if not request.user_ids:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "user_ids is empty"},
        )

    return MOCK_RECOMMENDATIONS_RESPONSE


@router.post(
    "/analyze_refresh",
    summary="사용자가 재추천을 원할 경우 호출하는 API",
    response_model=AnalyzeRefreshResponse,
)
async def analyze_refresh(request: AnalyzeRefreshRequest):
    """
    식당 재추천시 호출하는 API로 내부 그래프 처리 후 최종 5개의 식당 정보를 반환합니다.
    """
    if request.dining_data.dining_id is None:
        return JSONResponse(
            status_code=400,
            content={"message": "diningData.diningId is required"},
        )

    # analyze_refresh는 재추천이므로 is_refresh=True로 가정.
    # refresh_count나 투표 결과 처리는 graph 내부 로직에 위임.
    return MOCK_ANALYZE_REFRESH_RESPONSE


@router.post(
    "/restaurant_fix",
    summary="최종 식당 선택 확정 API",
    response_model=RestaurantFixResponse,
)
async def restaurant_fix(request: RestaurantFixRequest):
    """
    최종 식당 선택 확정 API
    - 사용자가 최종적으로 식당을 선택했을 때 호출
    - 로깅 및 DB 업데이트 등을 수행 (현재는 Mock 처리)
    """
    if not request.restaurant_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "restaurant_id is required"},
        )

    # TODO: 실제 확정 로직 구현 (DB 업데이트 등)

    return RestaurantFixResponse(
        success=True,
        restaurant_id=request.restaurant_id,
    )
