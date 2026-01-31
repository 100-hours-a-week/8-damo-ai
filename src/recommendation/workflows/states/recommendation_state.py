from typing import TypedDict, Annotated, List, Union
from datetime import datetime

def add_status_with_time(current: List[dict], new: Union[str, dict, List[Union[str, dict]]]) -> List[dict]:
    """메시지를 리스트에 추가할 때 자동으로 타임스탬프를 부여하는 리듀서"""
    if current is None: current = []
    
    # 입력이 리스트가 아니면 리스트로 변환
    if not isinstance(new, list):
        new = [new]
        
    formatted_new = []
    for item in new:
        if isinstance(item, str):
            # 문자열만 들어오면 딕셔너리로 변환 + 시간 추가
            formatted_new.append({"msg": item, "timestamp": datetime.now().isoformat()})
        elif isinstance(item, dict) and "msg" in item:
            # 딕셔너리인데 시간이 없으면 추가
            if "timestamp" not in item:
                item["timestamp"] = datetime.now().isoformat()
            formatted_new.append(item)
            
    # --- 중복 방지 로직 추가 ---
    # 이미 'current'에 존재하는 (메시지 내용 + 시간) 쌍은 제외하고 추가합니다.
    current_indices = set((m.get("msg"), m.get("timestamp")) for m in current)
    unique_new = [
        m for m in formatted_new 
        if (m.get("msg"), m.get("timestamp")) not in current_indices
    ]
    
    return current + unique_new

class RecommendationState(TypedDict):
    user_ids: List[int]
    dining_id: int
    dining_data: dict
    filtered_restaurants: List[dict]
    rejected_restaurants: List[dict]
    current_recommendation: dict
    personas: List[dict]

    status_message: Annotated[List[dict], add_status_with_time]
    iteration_count: int
    max_iterations: int
    user_satisfied: bool

    process_start_time: datetime
    process_time: float

    # 재시도 분기
    is_diffrent_user: bool
    is_empty_restaurants: bool

    # 투표 결과
    is_initial_workflow: bool
    vote_result_list: List[dict]

    # 에러 처리
    is_error: bool
    error_message: str
