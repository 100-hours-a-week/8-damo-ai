"""Recommendation task: 파이프라인 그래프 진입점."""
import logging
import time
from typing import Callable, Coroutine, Optional, Union

from shared.schemas.stream_schema import RecommendationRequestData, RecommendationRefreshRequestData
from services.recommendation.graph import build_pipeline_graph
from shared.monitoring import get_langfuse_handler, get_langfuse_client

logger = logging.getLogger(__name__)


async def recommendation_task(
    body: Union[RecommendationRequestData, RecommendationRefreshRequestData],
    correlation_id: str,
    log_type: str,
    on_persona_speak: Optional[Callable[[dict], Coroutine]] = None,
) -> dict:
    """통합 파이프라인 그래프 실행.

    Args:
        body: 추천 요청 데이터 (RecommendationRequestData | RecommendationRefreshRequestData)
        correlation_id: Kafka correlation_id (Langfuse session_id로 사용)
        log_type: "recommend" | "refresh"
        on_persona_speak: 페르소나 발언 시 호출할 콜백 (Kafka streaming 발행)
    """
    dining_id = body.dining_data.dining_id
    logger.info(
        "[%s] 파이프라인 시작: dining_id=%s, cid=%s",
        log_type.upper(),
        dining_id,
        correlation_id,
    )

    initial_state = {
        "user_ids": body.user_ids,
        "dining_id": dining_id,
        "dining_data": (
            body.dining_data.model_dump()
            if hasattr(body.dining_data, "model_dump")
            else body.dining_data
        ),
        "vote_result_list": getattr(body, "vote_result_list", []),
        "status_message": [
            f"{'추천' if log_type == 'recommend' else '리프레시'} 프로세스를 시작합니다."
        ],
        "iteration_count": 0,
        "max_iterations": 3,
        "is_initial_workflow": log_type == "recommend",
        "filtered_restaurant": [],
        "rejected_restaurant": [],
        "retry_count": 0,
    }

    # 테스트 모드: RunPod 호출 없이 목업 반환
    if body.dining_data.x == "DAMO_TEST":
        logger.info("[%s] 테스트 모드 — 목업 반환: dining_id=%s", log_type.upper(), dining_id)
        return {
            "filtered_restaurant": [],
            "dining_id": dining_id,
            "final_selection": [],
            "status_message": ["테스트 모드: 목업 데이터가 생성되었습니다."],
        }

    config = {
        "run_name": f"{log_type}-task",
        "configurable": {"on_persona_speak": on_persona_speak},
        "callbacks": [get_langfuse_handler()],
        "metadata": {
            "langfuse_user_id": f"{log_type}-{dining_id}",
            "langfuse_session_id": correlation_id,
            "langfuse_tags": [log_type],
            "correlation_id": correlation_id,
        },
    }

    t0 = time.monotonic()
    try:
        pipeline = build_pipeline_graph()
        final_state = await pipeline.ainvoke(initial_state, config=config)
        elapsed = time.monotonic() - t0
        logger.info(
            "[%s] 파이프라인 완료: dining_id=%s, final_selection=%d개, 소요=%.1fs",
            log_type.upper(),
            dining_id,
            len(final_state.get("final_selection", [])),
            elapsed,
        )
        get_langfuse_client().flush()
        return final_state
    except Exception:
        elapsed = time.monotonic() - t0
        logger.exception(
            "[%s] 파이프라인 실패: dining_id=%s, 소요=%.1fs",
            log_type.upper(),
            dining_id,
            elapsed,
        )
        return {
            "filtered_restaurant": [],
            "dining_id": dining_id,
            "final_selection": [],
            "status_message": ["파이프라인 오류가 발생했습니다."],
        }
