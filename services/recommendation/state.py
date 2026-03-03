from typing import TypedDict, Annotated, List, Union, Optional
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
    """
    Attributes:
        user_ids (List[int]): 추천에 참여하는 사용자 ID 리스트
        dining_id (Union[int, str]): 회식 세션 고유 ID
        dining_data (dict): 회식 기본 정보 (좌표, 예산, 날짜 등)
        filtered_restaurants (List[dict]): 필터링된 식당 후보 목록
        rejected_restaurants (List[dict]): 제외(거절)된 식당 목록
        vote_result_list (List[dict]): 이전 추천에 대한 투표 결과 리스트
        ---
        personas (List[dict]): 사용자 페르소나 분석 결과
        status_message (List[dict]): 실시간 진행 상황 메시지 (timestamp 포함)
        iteration_count (int): 현재 반복 횟수
        max_iterations (int): 최대 반복 횟수
        is_initial_workflow (bool): 최초 추천 가동 여부
        ---
        retry_count (int): AI 분석 재시도 횟수
        error_message (Optional[str]): 프로세스 중 발생한 에러 기록
        ---
        recommendation_count (int): 총 추천 수행 횟수
        recommended_items (List[dict]): 최종 추천 식당 TOP 5
    """
    # INPUT
    user_ids: List[int]
    dining_id: Union[int, str]
    dining_data: dict
    filtered_restaurant: List[dict]
    rejected_restaurant: List[dict]
    vote_result_list: List[dict]
    # PROCESS
    personas: List[dict]
    status_message: Annotated[List[dict], add_status_with_time]
    iteration_count: int                  # 현재 반복 횟수
    max_iterations: int                   # 최대 반복 횟수
    is_initial_workflow: bool             # 최초 추천 가동 여부
    needs_discussion: bool
    # ERROR
    retry_count: int                      # AI 분석 재시도 횟수
    error_message: Optional[str]          # 에러 발생 시 기록
    # OUTPUT
    recommendation_count: int
    recommended_items: List[dict]