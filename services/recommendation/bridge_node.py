"""Bridge node: recommendation → agent_dialogue 상태 연결.

filtered_restaurant(dict 리스트)에서 _id를 추출해 filtered_restaurant_ids(str 리스트)로 변환하고,
agent_dialogue 전용 필드를 초기화한다.
"""
import logging

from langfuse import observe

from services.recommendation.state import PipelineState

logger = logging.getLogger(__name__)


@observe(name="initialize_dialogue_state")
def bridge_node(state: PipelineState) -> dict:
    """filtered_restaurant → filtered_restaurant_ids 변환 + agent_dialogue 필드 초기화."""
    raw = state.get("filtered_restaurant", [])
    ids = [str(r.get("_id")) for r in raw if r.get("_id")]

    logger.info(
        "[BRIDGE] 식당 ID 추출 완료: %d개 → agent_dialogue 진입", len(ids)
    )

    return {
        "filtered_restaurant_ids": ids,
        # agent_dialogue 필드 초기화
        "user_data_list": [],
        "persona_prompts": {},
        "candidate_pool": [],
        "restaurant_offset": 0,
        "restaurant_index": 0,
        "recommended_restaurants": [],
        "processed_restaurants": [],
        "persona_votes": [],
        "dialogue_history": [],
        "is_error": False,
        "error_message": None,
    }
