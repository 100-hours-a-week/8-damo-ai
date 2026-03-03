import logging
from typing import Optional, Union
from shared.schemas.stream_schema import RecommendationRequestData, RecommendationRefreshRequestData
from services.recommendation.graph import get_recommendation_graph
from shared.monitoring import get_langfuse_client


async def recommendation_task(body: Union[RecommendationRequestData, RecommendationRefreshRequestData], correlation_id: str, log_type: str):
    logger = logging.getLogger("faststream")
    logger.info(f"[{log_type}] Starting process for dining_id: {body.dining_data.dining_id} [CID: {correlation_id}]")

    try:
        # LangGraph 실행
        initial_state = {
            "user_ids": body.user_ids,
            "dining_id": body.dining_data.dining_id,
            "dining_data": body.dining_data.model_dump() if hasattr(body.dining_data, 'model_dump') else body.dining_data,
            "vote_result_list": getattr(body, "vote_result_list", []),
            "status_message": [f"{'추천' if log_type == 'recommend' else '리프레시'} 프로세스를 시작합니다."],
            "iteration_count": 0,
            "max_iterations": 3,
            "is_initial_workflow": True if log_type == "recommend" else False,
            "needs_discussion": True,
        }

        if body.dining_data.x != "DAMO_TEST":
            recommendation_graph = get_recommendation_graph()
            from shared.monitoring import get_langfuse_handler
            config = {
                "run_name": f"{log_type}-task",
                "callbacks": [get_langfuse_handler()],
                "metadata": {
                    "langfuse_user_id": f"{log_type}-{str(body.dining_data.dining_id)}", 
                    "langfuse_session_id": correlation_id,  
                    "langfuse_tags": [f"{log_type}"],
                    "correlation_id": correlation_id
                }
            }
            final_state = await recommendation_graph.ainvoke(initial_state, config=config)
            from shared.monitoring import get_langfuse_client
            get_langfuse_client().flush()
            return final_state
        else:
            logger.info(f"[{log_type}] Skipping recommendation for user {body.dining_data.dining_id} (Test User)")
            return {
                "filtered_restaurant": ["201", "202", "203"],
                "status_message": ["테스트 모드: 목업 데이터가 생성되었습니다."]
            }
        
        logger.info(f"Background analysis completed successfully for dining_id: {body.dining_data.dining_id}")
    except Exception as e:
        logger.error(f"Error in recommendation for user {body.user_ids}: {str(e)}")
    