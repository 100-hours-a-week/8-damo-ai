from typing import Optional
from faststream import Logger
from shared.schemas.update_persona_db_request import UpdatePersonaDBRequest
from services.core_service.modules.persona.graph import get_persona_graph

async def analyze_persona_task(body: UpdatePersonaDBRequest, logger: Logger, correlation_id: Optional[str]):
    """백그라운드에서 수행될 페르소나 분석 및 DB 업로드 로직"""
    logger.info(f"Starting background persona analysis for user: {body.user_data.id} [CID: {correlation_id}]")
    
    try:
        # LangGraph 실행
        # TODO: 실제 DB를 조회하여 최초 생성 여부(is_first_time) 판단 로직 추가 필요
        initial_state = {
            "request_body": body,
            "is_first_time": True, 
            "retry_count": 0
        }

        if body.user_data.nickname != "DAMO_TEST":
            persona_graph = get_persona_graph()
            from shared.monitoring import get_langfuse_handler
            config = {
                "run_name": "persona-task",
                "callbacks": [get_langfuse_handler()],
                "metadata": {
                    "langfuse_user_id": f"user-{str(body.user_data.id)}", 
                    "langfuse_session_id": correlation_id,  
                    "langfuse_tags": ["persona"],
                    "correlation_id": correlation_id
                }
            }
            await persona_graph.ainvoke(initial_state, config=config)
            from shared.monitoring import get_langfuse_client
            get_langfuse_client().flush()
        
        logger.info(f"Background analysis completed successfully for user: {body.user_data.id}")
    except Exception as e:
        logger.error(f"Error in background persona analysis for user {body.user_data.id}: {str(e)}")