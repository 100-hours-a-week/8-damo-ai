"""협의 엔진 테스트 공통 픽스처."""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage


# ---------------------------------------------------------------------------
# 샘플 데이터
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_user_data_list() -> List[Dict[str, Any]]:
    return [
        {
            "id": 1,
            "nickname": "철수",
            "gender": "남성",
            "age_group": "20대",
            "allergies": ["땅콩"],
            "like_food_categories_id": ["한식", "일식"],
            "categories_id": ["한식", "일식", "중식"],
            "other_characteristics": "매운 음식 좋아함",
        },
        {
            "id": 2,
            "nickname": "영희",
            "gender": "여성",
            "age_group": "30대",
            "allergies": [],
            "like_food_categories_id": ["일식", "양식"],
            "categories_id": ["일식", "양식"],
            "other_characteristics": "",
        },
        {
            "id": 3,
            "nickname": "민수",
            "gender": "남성",
            "age_group": "20대",
            "allergies": ["갑각류"],
            "like_food_categories_id": ["한식"],
            "categories_id": ["한식", "분식"],
            "other_characteristics": "[System Insight] 이전 추천에서 일식을 거부함",
        },
    ]


@pytest.fixture
def sample_user_ids() -> List[int]:
    return [1, 2, 3]


@pytest.fixture
def sample_dining_data() -> Dict[str, Any]:
    return {
        "diningId": 100,
        "groupName": "점심 모임",
        "location": "강남역",
    }


@pytest.fixture
def sample_restaurant_docs() -> List[Dict[str, Any]]:
    return [
        {"_id": "r1", "place_name": "스시히로", "category_detail": "일식", "menus": [{"title": "초밥세트", "price": 15000}]},
        {"_id": "r2", "place_name": "김치찌개집", "category_detail": "한식", "menus": [{"title": "김치찌개", "price": 8000}]},
        {"_id": "r3", "place_name": "파스타하우스", "category_detail": "양식", "menus": [{"title": "크림파스타", "price": 13000}]},
        {"_id": "r4", "place_name": "짬뽕대왕", "category_detail": "중식", "menus": [{"title": "짬뽕", "price": 9000}]},
        {"_id": "r5", "place_name": "돈카츠전문", "category_detail": "일식", "menus": [{"title": "돈카츠", "price": 12000}]},
        {"_id": "r6", "place_name": "비빔밥천국", "category_detail": "한식", "menus": [{"title": "비빔밥", "price": 8500}]},
        {"_id": "r7", "place_name": "피자마루", "category_detail": "양식", "menus": [{"title": "마르게리타", "price": 18000}]},
        {"_id": "r8", "place_name": "우동집", "category_detail": "일식", "menus": [{"title": "우동", "price": 7500}]},
        {"_id": "r9", "place_name": "삼겹살집", "category_detail": "한식", "menus": [{"title": "삼겹살", "price": 14000}]},
        {"_id": "r10", "place_name": "탕수육집", "category_detail": "중식", "menus": [{"title": "탕수육", "price": 15000}]},
        {"_id": "r11", "place_name": "라멘가게", "category_detail": "일식", "menus": [{"title": "라멘", "price": 10000}]},
        {"_id": "r12", "place_name": "떡볶이집", "category_detail": "분식", "menus": [{"title": "떡볶이", "price": 5000}]},
    ]


@pytest.fixture
def sample_restaurant_ids() -> List[str]:
    return [f"r{i}" for i in range(1, 13)]


@pytest.fixture
def sample_consensus_candidates() -> List[Dict[str, Any]]:
    return [
        {"restaurant_id": "r1", "place_name": "스시히로", "reason": "일식 선호 다수"},
        {"restaurant_id": "r2", "place_name": "김치찌개집", "reason": "한식 선호 다수"},
        {"restaurant_id": "r3", "place_name": "파스타하우스", "reason": "양식 선호"},
        {"restaurant_id": "r6", "place_name": "비빔밥천국", "reason": "합리적 가격"},
        {"restaurant_id": "r5", "place_name": "돈카츠전문", "reason": "일식 인기"},
    ]


@pytest.fixture
def sample_dialogue_history() -> List[Dict[str, Any]]:
    return [
        {"user_id": "1", "nickname": "철수", "round": 1, "content": "스시히로가 좋겠어요. 초밥 좋아하니까."},
        {"user_id": "2", "nickname": "영희", "round": 1, "content": "저도 스시히로 좋아요. 파스타하우스도 괜찮고요."},
        {"user_id": "3", "nickname": "민수", "round": 1, "content": "저는 김치찌개집이 낫겠어요. 한식이 편해요."},
    ]


@pytest.fixture
def sample_persona_prompts() -> Dict[str, str]:
    return {
        "1": "당신은 철수입니다. 한식과 일식을 좋아합니다.",
        "2": "당신은 영희입니다. 일식과 양식을 좋아합니다.",
        "3": "당신은 민수입니다. 한식을 좋아합니다.",
    }


# ---------------------------------------------------------------------------
# Mock LLM
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm():
    """미리 정해진 응답을 반환하는 Mock LLM."""
    llm = MagicMock()

    async def _ainvoke(messages, config=None, **kwargs):
        return AIMessage(content="Mock LLM 응답입니다.")

    llm.ainvoke = AsyncMock(side_effect=_ainvoke)
    return llm


@pytest.fixture
def mock_llm_json_consensus():
    """합의 판정 JSON을 반환하는 Mock LLM (5개 합의)."""
    llm = MagicMock()
    json_response = """{
  "consensus_reached": true,
  "candidates": [
    {"restaurant_id": "r1", "place_name": "스시히로", "reason": "다수 찬성"},
    {"restaurant_id": "r2", "place_name": "김치찌개집", "reason": "한식 선호"},
    {"restaurant_id": "r3", "place_name": "파스타하우스", "reason": "양식 선호"},
    {"restaurant_id": "r6", "place_name": "비빔밥천국", "reason": "합리적 가격"},
    {"restaurant_id": "r5", "place_name": "돈카츠전문", "reason": "일식 인기"}
  ],
  "rejected": []
}"""

    async def _ainvoke(messages, config=None, **kwargs):
        return AIMessage(content=json_response)

    llm.ainvoke = AsyncMock(side_effect=_ainvoke)
    return llm


@pytest.fixture
def mock_llm_json_voting():
    """투표 JSON을 반환하는 Mock LLM."""
    llm = MagicMock()
    json_response = """{
  "votes": [
    {"restaurant_id": "r1", "place_name": "스시히로", "approve": true, "reasoning": "초밥 좋아요"},
    {"restaurant_id": "r2", "place_name": "김치찌개집", "approve": true, "reasoning": "한식 좋아요"},
    {"restaurant_id": "r3", "place_name": "파스타하우스", "approve": false, "reasoning": "양식 별로"},
    {"restaurant_id": "r6", "place_name": "비빔밥천국", "approve": true, "reasoning": "가격이 좋아요"},
    {"restaurant_id": "r5", "place_name": "돈카츠전문", "approve": true, "reasoning": "돈카츠 좋아요"}
  ]
}"""

    async def _ainvoke(messages, config=None, **kwargs):
        return AIMessage(content=json_response)

    llm.ainvoke = AsyncMock(side_effect=_ainvoke)
    return llm


@pytest.fixture
def mock_llm_no_consensus():
    """합의 미달 JSON을 반환하는 Mock LLM."""
    llm = MagicMock()
    json_response = """{
  "consensus_reached": false,
  "candidates": [],
  "rejected": []
}"""

    async def _ainvoke(messages, config=None, **kwargs):
        return AIMessage(content=json_response)

    llm.ainvoke = AsyncMock(side_effect=_ainvoke)
    return llm


@pytest.fixture
def mock_llm_partial_consensus():
    """부분 합의 (3개) JSON을 반환하는 Mock LLM."""
    llm = MagicMock()
    json_response = """{
  "consensus_reached": true,
  "candidates": [
    {"restaurant_id": "r1", "place_name": "스시히로", "reason": "다수 찬성"},
    {"restaurant_id": "r2", "place_name": "김치찌개집", "reason": "한식 선호"},
    {"restaurant_id": "r3", "place_name": "파스타하우스", "reason": "양식 선호"}
  ],
  "rejected": [
    {"restaurant_id": "r4", "place_name": "짬뽕대왕", "reason": "매운 음식 거부"}
  ]
}"""

    async def _ainvoke(messages, config=None, **kwargs):
        return AIMessage(content=json_response)

    llm.ainvoke = AsyncMock(side_effect=_ainvoke)
    return llm


# ---------------------------------------------------------------------------
# Mock DB
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db_manager(sample_user_data_list, sample_restaurant_docs):
    """DBManager를 mock하여 실제 DB 연결 없이 테스트."""
    user_map = {u["id"]: u for u in sample_user_data_list}
    restaurant_map = {r["_id"]: r for r in sample_restaurant_docs}

    async def _read_one(query):
        if "id" in query:
            return user_map.get(query["id"])
        if "diningId" in query:
            return None
        return None

    async def _read_all(query):
        if "$in" in query.get("_id", {}):
            ids = query["_id"]["$in"]
            return [restaurant_map[rid] for rid in ids if rid in restaurant_map]
        return []

    async def _update_one(query, update):
        pass

    db = MagicMock()
    db.read_one = AsyncMock(side_effect=_read_one)
    db.read_all = AsyncMock(side_effect=_read_all)
    db.update_one = AsyncMock(side_effect=_update_one)
    return db


# ---------------------------------------------------------------------------
# Langfuse Mock
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_langfuse():
    """모든 테스트에서 Langfuse 호출을 비활성화."""
    with patch(
        "services.iterative_discussion.app.utils.monitoring.init_consensus_trace",
        return_value="",
    ), patch(
        "services.iterative_discussion.app.utils.monitoring.create_langfuse_handler",
        return_value=None,
    ), patch(
        "services.iterative_discussion.app.utils.monitoring.create_graph_handler",
        return_value=None,
    ):
        yield
