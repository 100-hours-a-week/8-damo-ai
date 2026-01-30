import os
import json
from bson import ObjectId
from src.shared.db.db_manager import MongoManager
from src.recommendation.workflows.states.recommendation_state import RecommendationState
from src.shared.llm.llm_client import get_openai_llm
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from src.core.config import settings
from pydantic import BaseModel, Field
from typing import List
import asyncio
from time import time

os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
os.environ["LANGFUSE_BASE_URL"] = settings.LANGFUSE_BASE_URL
get_client()

class AllergyCheckResult(BaseModel):
    place_name: str = Field(..., description="식당 이름")
    is_safe: bool = Field(..., description="알러지 유발 메뉴를 제외하고도 먹을만한 메인 메뉴가 충분히 있는지 여부")
    reason: str = Field(..., description="안전 또는 차단 이유 요약")

class BatchAllergyCheckResult(BaseModel):
    results: List[AllergyCheckResult]

def __load_allergy_keywords():
    """알러지 키워드 데이터 로드"""
    keywords_map = {}
    path = os.path.join(os.getcwd(), "src/shared/json/allergies_keywords_ko.jsonl")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                keywords_map[data["allergy_type"]] = data["keywords"]
    return keywords_map

def __find_potential_risks(restaurant: dict, banned_keywords: list) -> list:
    """단순 키워드 매칭으로 위험 가능성이 있는 메뉴 선별"""
    risks = []
    menus = restaurant.get("menus", [])
    if not menus:
        return risks
        
    for menu in menus:
        title = menu.get("title", "")
        description = menu.get("description", "")
        menu_text = f"{title} {description}"
        
        for keyword in banned_keywords:
            if keyword in menu_text:
                risks.append({
                    "menu_title": title,
                    "menu_description": description,
                    "matched_keyword": keyword
                })
                break
    return risks

async def allergy_node(state: RecommendationState) -> RecommendationState:
    start_time = time()
    # Langfuse 클라이언트 초기화
    langfuse_handler = CallbackHandler()
    mongo = MongoManager()
    mongo.set_collection("user")
    keywords_map = __load_allergy_keywords()

    try:
        # 1. DB에서 사용자 정보 및 알러지 목록 수집
        _user_info = []
        _group_allergies = set()
        for user_id in state["user_ids"]:
            user = await mongo.read_one({"id": user_id})
            if user:
                _user_info.append(user)
                if user.get("allergies"):
                    for allergy in user["allergies"]:
                        _group_allergies.add(allergy)
        
        # print(f"그룹 통합 알러지 목록: {_group_allergies}")
        
        # 2. 알러지 유발 키워드 리스트 추출
        banned_keywords = []
        for allergy_type in _group_allergies:
            if allergy_type in keywords_map:
                banned_keywords.extend(keywords_map[allergy_type])
        
        # 3. 식당 필터링
        # 3-1. 검토 대상 식당 분류 (상위 30개만 진행)
        risky_restaurants = []
        final_restaurants = [] 
        
        target_restaurants = state["filtered_restaurants"][:30]
        
        for restaurant in target_restaurants:
            potential_risks = __find_potential_risks(restaurant, banned_keywords)
            if not potential_risks:
                final_restaurants.append(restaurant)
            else:
                risky_restaurants.append({
                    "place_name": restaurant.get('place_name'),
                    "menus": potential_risks,
                    "original_data": restaurant # 나중에 결과 매칭용
                })
        
        llm_agent = get_openai_llm()
        structured_llm = llm_agent.with_structured_output(BatchAllergyCheckResult)

        # 병렬 처리
        semaphore = asyncio.Semaphore(5)
        async def check_chunk(chunk):
            async with semaphore:
                # 1. 텍스트 최소화 (토큰 절약 및 속도 향상)
                items_to_check = []
                for r in chunk:
                    # 상위 3개 메뉴의 이름만 전달 (설명 제외)
                    short_menus = [m.get('title', '')[:20] for m in r.get("original_data", {}).get("menus", [])[:3]]
                    items_to_check.append({
                        "n": r["place_name"], # 키값도 짧게
                        "m": short_menus
                    })
                    
                # 2. 아주 짧고 강결한 지시
                prompt = f"알러지 {list(_group_allergies)} 기준 안전 검토. 메인 식사가능시 is_safe:true.\n{items_to_check}"
                
                # LLM 호출
                response = await structured_llm.ainvoke(
                    prompt, 
                    config={"callbacks": [langfuse_handler]}
                )
                return chunk, response.results

        # 2. 모든 배치(Chunk)를 태스크 리스트로 만들기
        tasks = []
        batch_size = 10
        for i in range(0, len(risky_restaurants), batch_size):
            chunk = risky_restaurants[i:i + batch_size]
            tasks.append(check_chunk(chunk))

        # 3. 병렬 실행 및 결과 취합
        # 모든 태스크가 끝날 때까지 기다립니다.
        all_results = await asyncio.gather(*tasks)
        # 4. 결과 매칭
        for chunk, batch_results in all_results:
            for res_item in batch_results:
                if res_item.is_safe:
                    original = next((r["original_data"] for r in chunk if r["place_name"] == res_item.place_name), None)
                    if original:
                        final_restaurants.append(original)
        end_time = time()
        print(f"알러지 필터링 완료: {len(final_restaurants)}개 검색됨 (가까운 순 정렬)")
        print(f"알러지 필터링 소요 시간: {end_time - start_time:.4f}초")
        return {
            "filtered_restaurants": final_restaurants, 
            "status_message": f"알러지 필터링 완료 : {len(final_restaurants)}개"
        }
    except Exception as e:
        print(f"알러지 필터링 중 오류 발생: {str(e)}")
        return {
            "is_error": True,
            "filtered_restaurants": [], 
            "status_message": f"알러지 필터링 중 오류 발생: {str(e)}"
        }