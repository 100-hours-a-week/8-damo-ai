import logging
from typing import Optional, Union
from services.core_service.modules.lightning.graph import get_lightning_graph
from shared.monitoring import get_langfuse_client

async def lightning_task(body: dict[str, str], correlation_id: str):
    logger = logging.getLogger("faststream")
    user_id = body.get("userId") or body.get("user_id")
    logger.info(f"[lightning] Starting process for user_id: {user_id} [CID: {correlation_id}]")

    try:
        initial_state = {
            "user_id": user_id,
            "x": body.get("x"),
            "y": body.get("y"),
        }

        lightning_graph = get_lightning_graph()
        from shared.monitoring import get_langfuse_handler
        config = {
            "run_name": f"lightning-task",
            "callbacks": [get_langfuse_handler()],
            "metadata": {
                "langfuse_user_id": f"lightning-{str(user_id)}", 
                "langfuse_session_id": correlation_id,  
                "langfuse_tags": [f"lightning"],
                "correlation_id": correlation_id
            }
        }
        final_state = await lightning_graph.ainvoke(initial_state, config=config)
        from shared.monitoring import get_langfuse_client
        get_langfuse_client().flush()
        
        # 프론트엔드 연동 명세에 맞게 결과 추출
        restaurants = final_state.get("filtered_restaurant", [])
        if not restaurants:
            return {"error": "조건에 맞는 식당을 찾을 수 없습니다."}

        best_res = restaurants[0]
        coords = best_res.get("location", {}).get("coordinates", [0, 0])
        res_x = str(coords[0]) if len(coords) > 0 else "0"
        res_y = str(coords[1]) if len(coords) > 1 else "0"

        return {
            "restaurantId": str(best_res.get("_id", "")),
            "restaurantName": best_res.get("name", best_res.get("place_name", "Unknown")),
            "x": res_x,
            "y": res_y,
            "phoneNumber": best_res.get("phone", best_res.get("tel", ""))
        }
    except Exception as e:
        logger.error(f"Error in lightning for user {user_id}: {str(e)}")

