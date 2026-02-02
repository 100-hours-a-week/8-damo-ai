from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from src.recommendation.schemas.update_persona_db_request import UpdatePersonaDBRequest
from src.recommendation.schemas.update_persona_db_response import (
    UpdatePersonaDBResponse,
)
from src.recommendation.schemas.recommendations_request import RecommendationsRequest
from src.recommendation.schemas.recommendations_response import RecommendationsResponse
from src.recommendation.schemas.restaurant_fix_request import RestaurantFixRequest
from src.recommendation.schemas.restaurant_fix_response import RestaurantFixResponse
from src.recommendation.data.mock_items import MOCK_RECOMMENDATIONS_RESPONSE
from src.recommendation.features.persona_manager.entities.users import Users
from src.recommendation.features.persona_manager.repositories.users_repository import (
    UsersRepository,
)
from src.recommendation.features.persona_manager.create_persona_description import (
    create_persona_description,
)
from src.shared.database import (
    create_dining_session,
    update_current_phase,
    finalize_dining_session,
)
from src.recommendation.workflows.workflow import recommendation_workflow
from src.shared.db.db_manager import MongoManager
import asyncio
from src.shared.llm.langfuse_handler import get_langfuse_callback, flush_langfuse, propagate_attributes

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

    try:
        # 1. LLM을 사용하여 페르소나 텍스트 생성
        persona_description = await create_persona_description(request)
        if persona_description == "TEST_MODE":
            return UpdatePersonaDBResponse(success=True, user_id=10101010)

        # 2. Users 엔티티 생성
        user_entity = Users(
            **request.user_data.model_dump(),
            reviews=request.review_data,
            base_persona=persona_description,
        )

        # 3. DB 저장
        repo = UsersRepository()
        saved_user = await repo.save(user_entity)

        return UpdatePersonaDBResponse(success=True, user_id=saved_user.id)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)},
        )


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

    try:
        # Langfuse 핸들러 생성 (recommendation: 추천 식별자)
        handler = get_langfuse_callback(
            prefix="recommendation",
            source_id=request.dining_data.dining_id
        )
        
        # 세션 ID 및 유저 ID 전파 (dining_id를 user_id로 활용)
        with propagate_attributes(
            session_id="recommendation", 
            user_id=str(request.dining_data.dining_id)
        ):
            result = await asyncio.wait_for(
                recommendation_workflow(request, callbacks=[handler]), 
                timeout=180.0
            )

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail={
                "error": "추천 프로세스가 너무 오래 걸려 중단되었습니다. 잠시 후 다시 시도해주세요."
            },
        )
    finally:
        flush_langfuse()

    if result.get("is_error") == True:
        raise HTTPException(
            status_code=400,
            detail={
                "error": result.get("error_message"),
            },
        )

    mongo = MongoManager()
    await mongo.save_dining_session(result)

    # 상위 5개 식당 매핑
    recommended_items = []
    for res in result.get("filtered_restaurants", [])[:5]:
        # 1. 추천 메뉴 요약 생성 (예: 삼겹살 4개, 소주 4개, ...)
        budget_rec = res.get("budget_recommendation", {})
        menu_details = budget_rec.get("menu_details", [])

        if menu_details:
            menu_summary = ", ".join(
                [f"{m['title']} {m['count']}개" for m in menu_details]
            )
        else:
            menu_summary = "추천 메뉴 구성 중"

        distance_m = res.get("distance", 0)
        reason = f"{menu_summary} | 거리: {distance_m}m"

        recommended_items.append(
            {
                "restaurant_id": str(res.get("id") or res.get("_id")),
                "score": float(res.get("total_score", 0.0)),
                "reasoning_description": reason[:500],
            }
        )

    return RecommendationsResponse(
        recommendation_count=result.get("iteration_count", 0),
        recommended_items=recommended_items,
    )


@router.post(
    "/analyze_refresh",
    summary="사용자가 재추천을 원할 경우 호출하는 API",
    response_model=RecommendationsResponse,
)
async def analyze_refresh(request: RecommendationsRequest):
    """
    식당 재추천시 호출하는 API로 내부 그래프 처리 후 최종 5개의 식당 정보를 반환합니다.
    """
    if request.dining_data.dining_id is None:
        return JSONResponse(
            status_code=400,
            content={"message": "diningData.diningId is required"},
        )

    try:
        # Langfuse 핸들러 생성 (analyze: 재분석 식별자)
        handler = get_langfuse_callback(
            prefix="analyze",
            source_id=request.dining_data.dining_id
        )
        
        # 세션 ID 및 유저 ID 전파 (dining_id를 user_id로 활용)
        with propagate_attributes(
            session_id="analyze", 
            user_id=str(request.dining_data.dining_id)
        ):
            result = await asyncio.wait_for(
                recommendation_workflow(request, callbacks=[handler]), 
                timeout=180.0
            )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail={
                "error": "추천 프로세스가 너무 오래 걸려 중단되었습니다. 잠시 후 다시 시도해주세요."
            },
        )
    finally:
        flush_langfuse()

    if result.get("is_error") == True:
        raise HTTPException(
            status_code=400,
            detail={
                "error": result.get("error_message"),
            },
        )

    mongo = MongoManager()
    await mongo.save_dining_session(result)

    # # 상위 5개 식당 매핑
    recommended_items = []
    for res in result.get("filtered_restaurants", [])[:5]:
        budget_rec = res.get("budget_recommendation", {})
        menu_details = budget_rec.get("menu_details", [])

        if menu_details:
            menu_summary = ", ".join(
                [f"{m['title']} {m['count']}개" for m in menu_details]
            )
        else:
            menu_summary = "추천 메뉴 구성 중"

        distance_m = res.get("distance", 0)
        reason = f"{menu_summary} | 거리: {distance_m}m"

        recommended_items.append(
            {
                "restaurant_id": str(res.get("id") or res.get("_id")),
                "score": float(res.get("total_score", 0.0)),
                "reasoning_description": reason[:500],
            }
        )

    return RecommendationsResponse(
        recommendation_count=result.get("iteration_count", 0),
        recommended_items=recommended_items,
    )


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

    result = await finalize_dining_session(
        request.dining_data.dining_id, request.restaurant_id
    )

    if not result.success:
        message = (
            "Session not found"
            if result.restaurant_id == ""
            else "Selected restaurant is not in candidates"
        )
        return JSONResponse(
            status_code=400, content={"success": False, "message": message}
        )

    return result
