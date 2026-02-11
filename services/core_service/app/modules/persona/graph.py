from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, START, END
from services.core_service.app.modules.bucket import bucket_manager
from shared.database.db_manager import DBManager
from shared.logging.logger import setup_logger
from shared.schemas.update_persona_db_request import UpdatePersonaDBRequest

# 로거 설정
logger = setup_logger("persona_graph")

# 1. State 정의: 분석 과정에서 공유될 데이터 구조
class PersonaState(TypedDict):
    request_body: UpdatePersonaDBRequest  # 입력 데이터
    is_first_time: bool                   # 최초 생성 여부 (분기 처리용)
    prompt_content: Optional[str]         # 외부 스토리지에서 가져온 프롬프트
    allergy_results: Optional[Dict]       # KAG 알러지 분석 결과
    persona_description: Optional[str]    # 최종 페르소나 설명
    retry_count: int                      # AI 분석 재시도 횟수
    error_message: Optional[str]          # 에러 발생 시 기록

# 2. 노드 함수 정의 (비즈니스 로직 단위)
async def fetch_prompt_node(state: PersonaState):
    """외부 스토리지(Bucket) 및 MongoDB에서 최신 프롬프트 로드 및 버저닝 체크"""
    logger.info("Node: Fetching Prompt & Versioning Check")
    
    user_id = state["request_body"].user_data.id
    
    # 1. 사용자 존재 여부 확인 (최초 생성 vs 업데이트 판단)
    db_manager = DBManager()
    db_manager.set_collection("users")
    existing_user = await db_manager.read_one(query={"id": user_id})
    
    is_first_time = existing_user is None
    logger.info(f"User {user_id} exists: {not is_first_time}")

    # 2. 프롬프트 로드 (기존 로직 유지)
    # TODO: bucket_manager 및 DBManager를 이용한 실제 버저닝 로직 구현
    
    return {
        "is_first_time": is_first_time,
        "prompt_content": "Current Persona Prompt Content",
        "retry_count": state.get("retry_count", 0)
    }

async def allergy_analysis_node(state: PersonaState):
    """KAG를 이용한 심층 메뉴 분석 (최초 생성 시에만 수행)"""
    logger.info("Node: Deep Allergy Analysis (KAG)")
    # TODO: LLM 연동 로직
    return {"allergy_results": {"status": "analyzed", "risk": "low"}}

async def persona_description_node(state: PersonaState):
    """정보 기반 페르소나 설명 생성"""
    logger.info("Node: Generating Persona Description")
    # TODO: LLM 연동 로직
    return {"persona_description": "Generated persona text for the user."}

async def save_db_node(state: PersonaState):
    """최종 분석 결과를 MongoDB(users 컬렉션)에 저장"""
    logger.info("Node: Saving Result to MongoDB")
    # TODO: DBManager 연동 로직
    return {}

# 3. 라우팅 함수 (분기 처리)

def route_performance(state: PersonaState):
    """최초 생성 시에는 알러지와 설명을 병렬로, 업데이트 시에는 설명만 처리"""
    if state.get("is_first_time", True):
        return ["allergy_analysis", "persona_description"]
    return ["persona_description"]

# 4. 그래프 구축

workflow = StateGraph(PersonaState)

# 노드 등록
workflow.add_node("fetch_prompt", fetch_prompt_node)
workflow.add_node("allergy_analysis", allergy_analysis_node)
workflow.add_node("persona_description", persona_description_node)
workflow.add_node("save_db", save_db_node)

# 에지 연결
workflow.add_edge(START, "fetch_prompt")

# 조건부 병렬 처리 (Fan-out)
workflow.add_conditional_edges(
    "fetch_prompt",
    route_performance,
    {
        "allergy_analysis": "allergy_analysis",
        "persona_description": "persona_description"
    }
)

# 결과 수렴 및 저장 (Fan-in)
workflow.add_edge("allergy_analysis", "save_db")
workflow.add_edge("persona_description", "save_db")
workflow.add_edge("save_db", END)

# 그래프 컴파일
persona_graph = workflow.compile()



