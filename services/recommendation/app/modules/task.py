from shared.logging.logger import setup_logger
from shared.schemas.recommendations_request import RecommendationsRequest
from services.recommendation.app.modules.graph import get_recommendation_graph
from shared.monitoring import get_langfuse_client

async def recommendation_task(body: RecommendationsRequest, correlation_id: str, log_type: str):
    logger = setup_logger(log_type)
    logger.info(f"Starting {log_type} for dining_id: {body.dining_data.dining_id}")

    try:
        # LangGraph 실행
        initial_state = {
            "user_ids": body.user_ids,
            "dining_id": body.dining_data.dining_id,
            "dining_data": body.dining_data.model_dump() if hasattr(body.dining_data, 'model_dump') else body.dining_data,
            "vote_result_list": body.vote_result_list or [],
            "status_message": [f"{'추천' if log_type == 'recommend' else '리프레시'} 프로세스를 시작합니다."],
            "iteration_count": 0,
            "max_iterations": 3,
            "is_initial_workflow": True if log_type == "recommend" else False
        }

        if body.dining_data.x != "DAMO_TEST":
            recommendation_graph = get_recommendation_graph()
            config = {
                "run_name": f"{log_type}-task",
                "metadata": {
                    "langfuse_user_id": f"{log_type}-{str(body.dining_data.dining_id)}", 
                    "langfuse_session_id": correlation_id,  
                    "langfuse_tags": [f"{log_type}"],
                    "correlation_id": correlation_id
                }
            }
            await recommendation_graph.ainvoke(initial_state, config=config)
            from shared.monitoring import get_langfuse_client
            get_langfuse_client().flush()
        else:
            logger.info(f"[{log_type}] Skipping recommendation for user {body.dining_data.dining_id} (Test User)")
        
        logger.info(f"Background analysis completed successfully for dining_id: {body.dining_data.dining_id}")
    except Exception as e:
        logger.error(f"Error in recommendation for user {body.user_ids}: {str(e)}")
    
