from services.core_service.modules.lightning.state import LightningState
from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph, START, END
from shared.database.db_manager import DBManager
from langgraph.types import Command
from shared.monitoring import get_langfuse_handler, get_langfuse_client
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from services.core_service.modules.persona.client import get_gemini_client


# 거리 노드
async def distance_node(state: LightningState) -> LightningState:
    db_manager = DBManager()
    db_manager.set_collection("restaurants")
    _X = float(state.get("x"))
    _Y = float(state.get("y"))
    MAX_DISTANCE = 2000 # 2km

    # 1. 거리 가까운 식당 가져오기
    restaurants = await db_manager.find_by_location(_X, _Y, MAX_DISTANCE)
    
    if not restaurants or len(restaurants) == 0:
        return Command(update={
            "filtered_restaurant": [],
            "status_message": "필터링된 식당이 없습니다",
            "error_message": f"No Restaurant from the location ({_X}, {_Y})"
        }, goto=END)

    # 2. 거리 점수 계산 (1.0 ~ 0.0)
    import math
    def calculate_haversine(lon1, lat1, lon2, lat2):
        R = 6371000 # 지구 반지름 (m)
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    for res in restaurants:
        res["_id"] = str(res["_id"]) # ObjectId를 문자열로 변환
        coords = res.get("location", {}).get("coordinates", [0, 0])
        dist = calculate_haversine(_X, _Y, coords[0], coords[1])
        
        # 가까울수록 1.0, 2km 지점이면 0.0
        score = max(0.0, 1.0 - (dist / MAX_DISTANCE))
        res["distance_score"] = round(score, 4)
        res["distance"] = int(dist) # 실제 거리(m)도 저장

    # 3. 점수 기반 정렬 (내림차순: 점수 높은/가까운 식당 우선)
    restaurants.sort(key=lambda x: x["distance_score"], reverse=True)

    return Command(update={
        "filtered_restaurant": restaurants,
        "status_message": f"거리 필터링 완료: {len(restaurants)}개 검색됨 (가까운 순 정렬)"
    }, goto="llm")

async def llm_node(state: LightningState) -> LightningState:
    restaurants = state.get("filtered_restaurant")[:10]
    new_candidates = []


    for data in restaurants:
        if data["menus"] and len(data["menus"]) > 0:
            new_candidates.append(data)
    
    if len(new_candidates) > 3:
        new_candidates = new_candidates[:3]
    
    # LLM 호출
    db_manager = DBManager()
    db_manager.set_collection("users")
    user = await db_manager.read_one({"id": int(state.get("user_id"))})

    persona_text = user["basePersona"]
    place_text = ""
    for new_candidate in new_candidates:
        menu_text = ""
        if new_candidate["menus"] and len(new_candidate["menus"]) > 3:
            for idx, menus in enumerate(new_candidate["menus"]):
                if idx < 3:
                    desc_text = ""
                    if menus['description'] is None or menus['description'] == "":
                        desc_text = "메뉴 설명이 없습니다."
                    else:
                        desc_text = menus['description']
                    menu_text += f"메뉴 이름: {menus['title']}, 메뉴 설명: {desc_text}\n"
                else:
                    break
        else:
            for menus in new_candidate["menus"]:
                desc_text = ""
                if menus['description'] is None or menus['description'] == "":
                    desc_text = "메뉴 설명이 없습니다."
                else:
                    desc_text = menus['description']
                menu_text += f"메뉴 이름: {menus['title']}, 메뉴 설명: {desc_text}\n"
        
        place_text += f"ID: {new_candidate['_id']}, 식당이름: {new_candidate.get('place_name', new_candidate.get('name', 'Unknown'))}, 메뉴: {menu_text}\n"
    
    # LLM 프롬프트 및 호출
    prompt_template = """당신은 회식 장소를 추천하는 AI 전문가입니다.
유저의 페르소나와 현재 위치 주변의 식당 후보군을 제공합니다.
이 중에서 유저의 취향에 가장 잘 맞을 것 같은 식당 1곳만 추천해주세요.
반드시 응답은 아래 JSON 형식으로만 해주세요 (마크다운 없이 순수 JSON 객체만).

[유저 페르소나]
{persona_text}

[식당 후보군]
{place_text}

[출력 형식]
{{
    "restaurant_id": "선택한 식당의 ID 값",
    "reason": "추천 사유 (유저 페르소나와 연관지어 1~2줄로 설명)"
}}"""

    llm = get_gemini_client(model="gemini-3-flash-preview", temperature=0.7)
    chain = ChatPromptTemplate.from_template(prompt_template) | llm | StrOutputParser()

    try:
        response_str = await chain.ainvoke({"persona_text": persona_text, "place_text": place_text})
        
        # 응답 파싱 (마크다운 제거)
        clean_json_str = response_str.strip(" `\n").removeprefix("json\n")
        response_data = json.loads(clean_json_str)
        
        selected_id = response_data.get("restaurant_id")
        reason = response_data.get("reason", "LLM 필터링 완료")
        
        # 선택된 식당 찾기
        selected_res = next((res for res in new_candidates if str(res["_id"]) == selected_id), new_candidates[0])
        
        return Command(update={
            "filtered_restaurant": [selected_res],
            "status_message": f"LLM 추천 완료: {reason}"
        }, goto=END)
        
    except Exception as e:
        print(f"LLM Error: {e}")
        # 에러 시 그냥 첫 번째 식당 반환
        return Command(update={
            "filtered_restaurant": [new_candidates[0]] if new_candidates else restaurants,
            "status_message": "LLM 필터링 실패, 기본 정렬된 첫 번째 식당 반환"
        }, goto=END)

# 메인 그래프
def get_lightning_graph() -> Runnable:
    workflow = StateGraph(LightningState)
    workflow.add_node("distance", distance_node)
    workflow.add_node("llm", llm_node)

    workflow.add_edge(START, "distance")
    workflow.add_edge("distance", "llm")
    workflow.add_edge("llm", END)
    
    handler = get_langfuse_handler()
    
    return workflow.compile().with_config({"callbacks": [handler]})