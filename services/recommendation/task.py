"""Recommendation task: 파이프라인 그래프 진입점."""
import logging
import time
from typing import Callable, Coroutine, Optional, Union

from shared.monitoring import get_langfuse_handler  # env var 주입을 위해 graph보다 먼저 임포트
# [EOS] from shared.checkpoint import get_checkpointer
from shared.schemas.stream_schema import RecommendationRequestData, RecommendationRefreshRequestData
from services.recommendation.graph import build_pipeline_graph

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
            "dining_data": initial_state["dining_data"],
            "final_selection": [],
            "status_message": ["테스트 모드: 목업 데이터가 생성되었습니다."],
        }

    t0 = time.monotonic()
    try:
        # [EOS] checkpointer = get_checkpointer()
        pipeline = build_pipeline_graph()
        # [EOS] pipeline = build_pipeline_graph(checkpointer=checkpointer)
        handler = get_langfuse_handler()
        config = {
            "run_name": f"{log_type}-pipeline",
            "configurable": {
                "on_persona_speak": on_persona_speak,
                # [EOS] "thread_id": str(dining_id),  # 체크포인터 재개용
            },
            "callbacks": [handler] if handler else [],
        }
        # [EOS] 체크포인트 감지 및 재개 로직 (EOS 활성화 시 아래 주석 해제):
        # [EOS] graph_input: dict | None = initial_state
        # [EOS] if checkpointer is not None:
        # [EOS]     existing = await checkpointer.aget_tuple(config)
        # [EOS]     if existing is not None:
        # [EOS]         logger.info("[%s] 체크포인트 복원 → 이어서 실행: dining_id=%s", log_type.upper(), dining_id)
        # [EOS]         graph_input = None  # ainvoke(None): 체크포인트 상태를 그대로 사용
        # [EOS]         # ※ ainvoke(initial_state)를 넘기면 체크포인트 필드(filtered_restaurant 등)를
        # [EOS]         #   초기값으로 덮어써 처음부터 재실행하게 된다 — 반드시 None을 사용할 것

        logger.info("[%s] 그래프 ainvoke 시작", log_type.upper())
        final_state = await pipeline.ainvoke(initial_state, config=config)
        logger.info(
            "[%s] 그래프 ainvoke 완료: is_error=%s, filtered_restaurant=%d개, final_selection=%d개",
            log_type.upper(),
            final_state.get("is_error"),
            len(final_state.get("filtered_restaurant", [])),
            len(final_state.get("final_selection", [])),
        )
        elapsed = time.monotonic() - t0
        logger.info(
            "[%s] 파이프라인 완료: dining_id=%s, final_selection=%d개, 소요=%.1fs",
            log_type.upper(),
            dining_id,
            len(final_state.get("final_selection", [])),
            elapsed,
        )
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
            "dining_data": initial_state["dining_data"],
            "final_selection": [],
            "status_message": ["파이프라인 오류가 발생했습니다."],
        }
