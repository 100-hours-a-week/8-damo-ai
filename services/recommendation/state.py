from typing import TypedDict, Annotated, List, Union, Optional, Any, Dict
from datetime import datetime


def add_status_with_time(
    current: List[dict], new: Union[str, dict, List[Union[str, dict]]]
) -> List[dict]:
    """메시지를 리스트에 추가할 때 자동으로 타임스탬프를 부여하는 리듀서"""
    if current is None:
        current = []

    if not isinstance(new, list):
        new = [new]

    formatted_new = []
    for item in new:
        if isinstance(item, str):
            formatted_new.append({"msg": item, "timestamp": datetime.now().isoformat()})
        elif isinstance(item, dict) and "msg" in item:
            if "timestamp" not in item:
                item["timestamp"] = datetime.now().isoformat()
            formatted_new.append(item)

    current_indices = set((m.get("msg"), m.get("timestamp")) for m in current)
    unique_new = [
        m for m in formatted_new
        if (m.get("msg"), m.get("timestamp")) not in current_indices
    ]

    return current + unique_new


class PipelineState(TypedDict):
    """recommendation + agent_dialogue 통합 파이프라인 상태."""

    # ── 공통 입력 ──────────────────────────────────────────────────────────
    user_ids: List[int]
    dining_id: Union[int, str]
    dining_data: Dict[str, Any]
    vote_result_list: List[Dict[str, Any]]

    # ── Recommendation 출력 ───────────────────────────────────────────────
    filtered_restaurant: List[Dict[str, Any]]    # 전체 식당 객체
    rejected_restaurant: List[Dict[str, Any]]
    personas: List[Dict[str, Any]]
    status_message: Annotated[List[dict], add_status_with_time]
    iteration_count: int
    max_iterations: int
    is_initial_workflow: bool
    retry_count: int

    # ── Bridge 출력 ────────────────────────────────────────────────────────
    filtered_restaurant_ids: List[str]           # bridge: filtered_restaurant에서 _id 추출

    # ── AgentDialogue 전용 ─────────────────────────────────────────────────
    user_data_list: List[Dict[str, Any]]
    persona_prompts: Dict[str, str]
    candidate_pool: List[Dict[str, Any]]
    restaurant_offset: int
    restaurant_index: int
    dialogue_history: List[Dict[str, Any]]
    recommended_restaurants: List[Dict[str, Any]]
    processed_restaurants: List[Dict[str, Any]]
    persona_votes: List[Dict[str, Any]]

    # ── 최종 출력 ──────────────────────────────────────────────────────────
    final_selection: List[Dict[str, Any]]        # [{restaurant_id, place_name, reason}, ...]

    # ── 에러 처리 ──────────────────────────────────────────────────────────
    is_error: bool
    error_message: Optional[str]


# 서브그래프(recommend_sg, refresh_sg) 호환 별칭
RecommendationState = PipelineState
