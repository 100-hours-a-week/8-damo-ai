import os, re, yaml
from datetime import datetime
from typing import TypedDict, Optional, Dict
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from services.core_service.app.modules.bucket import bucket_manager
from services.core_service.app.modules.persona.client import get_gemini_client
from shared.database.db_manager import DBManager
from shared.logging.logger import setup_logger
from shared.schemas.update_persona_db_request import UpdatePersonaDBRequest
from shared.monitoring import get_langfuse_handler, get_langfuse_client

get_langfuse_client()

# 로거 설정
logger = setup_logger("core_service_persona_graph")

## TODO: 확장성 고려를 위한 분기 노드
"""
async def allergy_analysis_node(state: PersonaState):
    # KAG를 이용한 심층 메뉴 분석 (최초 생성 시에만 수행)
    logger.info("Node: Deep Allergy Analysis (KAG)")
    return {"allergy_results": {"status": "analyzed", "risk": "low"}}
"""
"""
# 3. 라우팅 함수 (분기 처리)
def route_performance(state: PersonaState):
    # 최초 생성 시에는 알러지와 설명을 병렬로, 업데이트 시에는 설명만 처리
    if state.get("is_first_time", True):
        return ["allergy_analysis", "persona_description"]
    return ["persona_description"]
"""

# 1. State 정의: 분석 과정에서 공유될 데이터 구조
class PersonaState(TypedDict):
    # INPUT
    request_body: UpdatePersonaDBRequest  # 입력 데이터
    # PROCESS
    prompt_content: Optional[str]         # 외부 스토리지에서 가져온 프롬프트
    metadata: Optional[Dict]              # 프롬프트 메타데이터
    prompt_template: Optional[str]        # 프롬프트 템플릿
    input_data: Optional[Dict]            # AI 입력 데이터
    # ERROR
    retry_count: int                      # AI 분석 재시도 횟수
    error_message: Optional[str]          # 에러 발생 시 기록
    # OUTPUT
    persona_description: Optional[str]    # 최종 페르소나 설명

def load_prompt_system(raw_content):
    # 정규식으로 metadata와 markdown 분리
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)'
    match = re.search(pattern, raw_content, re.DOTALL | re.MULTILINE)
    
    if match:
        # 1. 메타데이터 (JSON 또는 YAML 형태)
        metadata_raw = match.group(1)
        # 2. 실제 프롬프트 내용
        prompt_body = match.group(2).strip()
        # 메타데이터를 딕셔너리로 변환 (YAML 기준)
        metadata = yaml.safe_load(metadata_raw)
        return metadata, prompt_body
    
    return {}, raw_content

# 재시도 로직
def should_retry(state: PersonaState):
    """에러 발생 시 최대 3회까지 재시도 여부 결정"""
    if state.get("error_message") and state.get("retry_count", 0) < 3:
        logger.info(f"Retry: Attempting {state['retry_count']}...")
        return "retry"
    
    return "finish"

# 2. 노드 함수 정의 (비즈니스 로직 단위)
async def fetch_prompt_node(state: PersonaState, config: RunnableConfig):
    """외부 스토리지(Bucket) 및 MongoDB에서 최신 프롬프트 로드 및 버저닝 체크"""
    logger.info("Node: Fetching Prompt & Versioning Check")

    # 프롬프트 버전 체크
    db_manager = DBManager()
    db_manager.set_collection("prompts")
    prompt = await db_manager.read_one(query={"service": "persona"})
    prompt_file_name = f"persona_{prompt['shouldUseVersion']}.md"
    
    bucket_manager.download_file(f"persona/{prompt_file_name}", f"/tmp/{prompt_file_name}")
    
    with open(f"/tmp/{prompt_file_name}", "r") as f:
        raw_content = f.read()

    os.remove(f"/tmp/{prompt_file_name}")
    
    return {
        "prompt_content": raw_content,
        "retry_count": state.get("retry_count", 0)
    }

async def prep_data_node(state: PersonaState, config: RunnableConfig):
    """입력 데이터 정제화"""
    logger.info("Node: Preparing Data for AI")
    metadata, prompt_template = load_prompt_system(state["prompt_content"])

    user_data = state["request_body"].user_data
    review_data = state["request_body"].review_data

    allergies = ", ".join([a.value for a in user_data.allergies])
    like_food_categories = ", ".join(user_data.categories_id)
    preferred_ingredients = ", ".join(user_data.like_food_categories_id)

    input_data = {
        "nickname": user_data.nickname,
        "gender": user_data.gender.value,
        "age_group": user_data.age_group.value,
        "allergies": allergies,
        "like_food_categories": like_food_categories,
        "preferred_ingredients": preferred_ingredients,
        "other_characteristics": user_data.other_characteristics,
        "reviews": [
            f"- {r.restaurant_id} | {r.rating}점 | {r.comment}"
            for r in review_data
        ] if review_data else "없음"
    }

    return {
        "metadata": metadata,
        "prompt_template": prompt_template,
        "input_data": input_data
    }

async def persona_description_node(state: PersonaState, config: RunnableConfig):
    """정보 기반 페르소나 설명 생성"""
    logger.info("Node: Generating Persona Description")
    # 에러 초기화
    
    metadata = state["metadata"]
    prompt_template = state["prompt_template"]
    input_data = state["input_data"]
    
    llm = get_gemini_client(
        model=metadata.get("model", "gemini-3-flash-preview"),
        temperature=metadata.get("temperature", 0.7)
    )
    
    try:
        chain = ChatPromptTemplate.from_template(prompt_template) | llm | StrOutputParser()
        if isinstance(input_data["reviews"], list):
            input_data["reviews"] = "\n".join(input_data["reviews"])
        response = await chain.ainvoke(input_data, config=config) 
        
        return {"persona_description": response, "error_message": None}
    except Exception as e:
        logger.error(f"Chain execution failed: {str(e)}")
        return {"error_message": str(e), "retry_count": state.get("retry_count", 0) + 1}

async def save_db_node(state: PersonaState, config: RunnableConfig):
    """최종 분석 결과를 MongoDB(users 컬렉션)에 저장"""
    logger.info("Node: Saving Result to MongoDB")    
    db_manager = DBManager()
    db_manager.set_collection("users")
    user_data = state["request_body"].user_data
    review_data = state["request_body"].review_data

    # 기본 정보 업데이트(추후 로직 확정시 하나로 결합 필요)
    await db_manager.update_one_with_command(
        filter_query={"id": user_data.id},
        update_command={
            "$set": {
                "nickname": user_data.nickname,  # 새 유저일 때를 대비해 기본 정보도 포함
                "gender": user_data.gender.value if hasattr(user_data.gender, 'value') else user_data.gender,
                "ageGroup": user_data.age_group.value if hasattr(user_data.age_group, 'value') else user_data.age_group,
                "allergies": [a.value if hasattr(a, 'value') else a for a in user_data.allergies],
                "likeFoods": getattr(user_data, "categories_id", []),
                "likeIngredients": getattr(user_data, "like_food_categories_id", []),
                "otherCharacteristics": user_data.other_characteristics,
                "reviews": [r.model_dump() if hasattr(r, 'model_dump') else r for r in review_data],
                "updatedAt": datetime.now()
            },
            "$setOnInsert": {
                "createdAt": datetime.now()  # 처음 생성될 때만 기록
            }
        },
        upsert=True
    )
    
    # 저장 방법 1. 스트링 덮어쓰기
    # update_one은 내부적으로 {"$set": update_data}를 수행합니다.
    if state.get("error_message") is None:
        logger.info("Final Status: Success")
        await db_manager.update_one(
            filter_query={"id": user_data.id},
            update_data={"basePersona": state["persona_description"]},
            upsert=True
        )
    else:
        # 3회 재시도 후에도 에러가 남아있는 경우
        logger.error(f"Final Status: Failed after retries. Error: {state['error_message']}")
        await db_manager.update_one(
            filter_query={"id": user_data.id},
            update_data={"basePersona": f"ERROR: {state['error_message']}"},
            upsert=True
        )
    # 저장 방법 2. 히스토리 누적 (History Object Array)
    # new_entry = {
    #     "description": state["persona_description"],
    #     "updatedAt": datetime.now()  # 현재 시간 기록
    # }
    
    # await db_manager.update_one_with_command(
    #     filter_query={"id": state["request_body"].user_data.id},
    #     update_command={
    #         "$push": {
    #             "basePersona": {
    #                 "$each": [new_entry],
    #                 "$sort": {"updatedAt": -1},
    #                 "$slice": 10
    #             }
    #         }
    #     }
    # )

    logger.info("Node: Saved Result to MongoDB Completed")
    return {}


# 메인 그래프
def get_persona_graph():
    # 그래프 구축
    workflow = StateGraph(PersonaState)

    # 노드 등록
    workflow.add_node("fetch_prompt", fetch_prompt_node)
    workflow.add_node("prep_data", prep_data_node)
    workflow.add_node("persona_description", persona_description_node)
    workflow.add_node("save_db", save_db_node)

    # 에지 연결
    workflow.add_edge(START, "fetch_prompt")
    workflow.add_edge("fetch_prompt", "prep_data")
    workflow.add_edge("prep_data", "persona_description")
    # 조건부 에지 추가: persona_description 이후의 흐름 결정
    workflow.add_conditional_edges(
        "persona_description",
        should_retry,
        {
            "retry": "persona_description",  # 자기 자신에게 루프
            "finish": "save_db"              # 성공했거나 3회 실패 시 DB로
        }
    )
    workflow.add_edge("save_db", END)

    handler = get_langfuse_handler()

    # 그래프 컴파일
    return workflow.compile().with_config({"callbacks": [handler]})




