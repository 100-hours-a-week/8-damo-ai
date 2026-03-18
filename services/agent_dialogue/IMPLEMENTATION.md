# agent_dialogue 구현 계획

설계 확정 기준: DESIGN.md 참조
구현 순서는 의존성 기준으로 정렬.

---

## Langfuse 프롬프트 관리 가이드

### 타입 구분

| 타입 | Langfuse 등록 방식 | 코드에서 사용 함수 | 반환값 |
|---|---|---|---|
| **text** | 단일 문자열 (`{{variable}}` 포맷) | `get_prompt(name, fallback, **vars)` | `(str, prompt_obj)` |
| **chat** | 메시지 배열 (`role` + `content`) | `get_chat_prompt(name, fallback_messages, **vars)` | `(List[BaseMessage], prompt_obj)` |

- `text` 타입: SystemMessage/HumanMessage 중 하나로 직접 감싸서 LLM에 전달
- `chat` 타입: 여러 메시지(system + user, 또는 placeholder 포함)로 구성되어 그대로 LLM에 전달

### 신규 프롬프트 전체 목록

| Langfuse 이름 | 타입 | fallback 상수 | 사용 노드 | 변수 |
|---|---|---|---|---|
| `restaurant-analyst-speak` | **text** | `ANALYST_SPEAK_PROMPT` | `restaurant_dialogue` | `restaurant_info`, `dining_info`, `allergy_info` |
| `restaurant-persona-react` | **chat** | `PERSONA_REACT_CHAT_FALLBACK` | `restaurant_dialogue` | `analyst_speech`, `previous_reactions` |
| `restaurant-persona-vote` | **chat** | `PERSONA_VOTE_CHAT_FALLBACK` | `restaurant_dialogue` | `analyst_speech`, `all_reactions` |

### 기존 재사용 프롬프트 (iterative_discussion에서 그대로 유지)

| Langfuse 이름 | 타입 | 사용 노드 |
|---|---|---|
| `persona-system-prompt` | **text** | `persona_factory` |

### 코드 패턴

#### text 타입 (`get_prompt`)

```python
from agent_dialogue.app.prompts.langfuse_prompts import get_prompt
from agent_dialogue.app.prompts.restaurant_templates import ANALYST_SPEAK_PROMPT

user_prompt, lf_prompt = get_prompt(
    "restaurant-analyst-speak",
    ANALYST_SPEAK_PROMPT,
    restaurant_info=restaurant_info,
    dining_info=dining_info,
    allergy_info=allergy_info,
)

response = await llm.ainvoke([
    SystemMessage(content=ANALYST_SYSTEM_PROMPT),
    HumanMessage(content=user_prompt),
])
```

#### chat 타입 (`get_chat_prompt`)

```python
from agent_dialogue.app.prompts.langfuse_prompts import get_chat_prompt
from agent_dialogue.app.prompts.restaurant_templates import PERSONA_REACT_CHAT_FALLBACK

messages, lf_prompt = get_chat_prompt(
    "restaurant-persona-react",
    PERSONA_REACT_CHAT_FALLBACK,
    analyst_speech=analyst_speech,
    previous_reactions=previous_reactions,
)

response = await llm.ainvoke(
    [SystemMessage(content=persona_system_prompt)] + messages
)
```

#### Langfuse generation 연동 (모든 LLM 호출 공통)

```python
lf_handler = make_callback_handler()
lf_config = {"callbacks": [lf_handler], "metadata": {"user_id": user_id}}

response = await llm.ainvoke(messages, config=lf_config)
```

---

## Phase 1. 기반 파일

의존성이 없는 파일부터 생성. 대부분 복사 또는 단순 수정.

---

### 1-1. `__init__.py` 파일 (6개)

빈 파일로 생성.

```
services/agent_dialogue/__init__.py
services/agent_dialogue/app/__init__.py
services/agent_dialogue/app/engine/__init__.py
services/agent_dialogue/app/nodes/__init__.py
services/agent_dialogue/app/prompts/__init__.py
services/agent_dialogue/app/utils/__init__.py
```

---

### 1-2. `app/utils/logging_config.py`

**원본:** `iterative_discussion/app/utils/logging_config.py`
**처리:** 그대로 복사 (변경 없음)

---

### 1-3. `app/utils/monitoring.py`

**원본:** `iterative_discussion/app/utils/monitoring.py`
**변경:** trace 함수명만 변경

```python
# before
def init_consensus_trace(...)

# after
def init_agent_dialogue_trace(...)
```

---

### 1-4. `app/utils/scoring.py`

**원본:** `iterative_discussion/app/utils/scoring.py`
**처리:** 그대로 복사 (변경 없음)

---

### 1-5. `app/engine/llm_factory.py`

**원본:** `iterative_discussion/app/engine/llm_factory.py`
**처리:** 그대로 복사 (변경 없음)

---

### 1-6. `app/prompts/langfuse_prompts.py`

**원본:** `iterative_discussion/app/prompts/langfuse_prompts.py`
**처리:** 그대로 복사 (변경 없음)

---

### 1-7. `app/prompts/persona_templates.py`

**원본:** `iterative_discussion/app/prompts/persona_templates.py`
**처리:** 그대로 복사 (변경 없음)

---

## Phase 2. State & Graph

---

### 2-1. `app/engine/state.py`

**신규 작성**

```python
class AgentDialogueState(TypedDict):
    # 입력
    user_ids: List[int]
    user_data_list: List[Dict[str, Any]]
    dining_data: Dict[str, Any]
    filtered_restaurant_ids: List[str]   # 전체 후보 ID 목록 (외부 입력)
    vote_result_list: List[Dict[str, Any]]  # 재추천 시 thumbup/thumbdown

    # Node 1: persona_factory
    persona_prompts: Dict[str, str]      # user_id → system prompt

    # Node 2: moderator_preselect
    candidate_pool: List[Dict[str, Any]] # 현재 배치 식당 (최대 5개, score 포함)
    restaurant_offset: int               # filtered_restaurant_ids에서 다음 fetch 시작 위치

    # Node 3: restaurant_dialogue
    restaurant_index: int                # 현재 배치 내 처리 중인 인덱스 (0 ~ batch_size-1)
    dialogue_history: List[Dict[str, Any]]  # 전체 대화 기록 (분석가 + 반응 + 투표)
    recommended_restaurants: List[Dict[str, Any]]  # 과반수 통과 식당 (최대 5개)
    processed_restaurants: List[Dict[str, Any]]    # 투표 완료된 모든 식당 (fallback용)

    # 최종 출력
    final_selection: List[Dict[str, Any]]  # 최종 Top 5
    persona_votes: List[Dict[str, Any]]    # 전체 투표 기록 (self_evolution 저장용)

    # 에러 처리
    is_error: bool
    error_message: str
```

`create_initial_state()` 팩토리 함수:
- 파라미터: `user_ids`, `dining_data`, `filtered_restaurant_ids`, `vote_result_list=None`
- `restaurant_offset=0`, `restaurant_index=0` 초기화
- `candidate_pool=[]`, `dialogue_history=[]`, `recommended_restaurants=[]`, `processed_restaurants=[]`, `persona_votes=[]` 초기화

---

### 2-2. `app/engine/graph.py`

**신규 작성**

조건부 엣지 함수:

```python
def _check_error(state) -> str:
    return "end" if state.get("is_error") else "continue"

def _after_restaurant_dialogue(state) -> str:
    if state.get("is_error"):
        return "end"

    # 5개 채움 → 종료
    if len(state["recommended_restaurants"]) >= 5:
        return "end"

    # 현재 배치에 남은 식당 → 계속
    if state["restaurant_index"] < len(state["candidate_pool"]):
        return "restaurant"

    # 배치 완료 + 추가 ID 있음 → 다음 배치 fetch
    offset = state.get("restaurant_offset", 0)
    total = len(state.get("filtered_restaurant_ids", []))
    if offset < total:
        return "preselect"

    # 모두 소진 → fallback 후 종료
    return "end"
```

노드 등록 및 엣지 연결:

```
persona_factory   →(_check_error)→  moderator_preselect
                                  → END
moderator_preselect →(_check_error)→ restaurant_dialogue
                                   → END
restaurant_dialogue →(_after_restaurant_dialogue)→ restaurant_dialogue (루프)
                                                 → moderator_preselect (배치 루프백)
                                                 → END
```

빌드 함수: `build_agent_dialogue_graph() -> CompiledGraph`

---

## Phase 3. 재사용 노드

import 경로를 `iterative_discussion` → `agent_dialogue`로 변경.

---

### 3-1. `app/nodes/persona_factory.py`

**원본:** `iterative_discussion/app/nodes/persona_factory.py`
**변경:** import 경로 변경 + self_evolution 로직 통합

추가 처리 (self_evolution 통합):
```python
# vote_result_list가 있으면 (재추천):
# - dining_sessions DB 조회 → 이전 가상투표 조회
# - 예측 vs 실제 비교 → best_case / worst_case 텍스트 생성
# - 각 페르소나 프롬프트의 {vote_feedback} 자리에 주입
if state.get("vote_result_list"):
    vote_feedback = _build_vote_feedback(...)
    # persona_prompts 각각에 vote_feedback 주입
```

---

### 3-2. `app/nodes/moderator_preselect.py`

**원본:** `iterative_discussion/app/nodes/moderator_preselect.py`
**변경:** import 경로 변경 + batch/offset 로직 추가, `top_k` 10 → 5

처리 순서:
1. `restaurant_offset`부터 최대 5개 ID 슬라이싱: `filtered_restaurant_ids[offset : offset+5]`
2. DB에서 해당 식당 문서 조회
3. `rank_restaurants()`로 score 정렬
4. `restaurant_offset += len(batch)`, `restaurant_index = 0` 리셋 반환

```python
async def moderator_preselect(state: AgentDialogueState) -> dict:
    offset = state.get("restaurant_offset", 0)
    batch_ids = state["filtered_restaurant_ids"][offset : offset + 5]
    # ... DB 조회, score 정렬 ...
    return {
        "candidate_pool": ranked,
        "restaurant_offset": offset + len(batch_ids),
        "restaurant_index": 0,
    }
```

---

## Phase 4. 신규 프롬프트

---

### 4-1. `app/prompts/restaurant_templates.py`

**신규 작성** — 분석가 발언 + 페르소나 반응 + 페르소나 투표 프롬프트

```python
# ── 통합 분석가 시스템 프롬프트 ────────────────────────────────────────────
ANALYST_SYSTEM_PROMPT = """\
당신은 회식 장소 선정 전문 분석가입니다.
주어진 식당 데이터를 바탕으로 알레르기 위험, 메뉴 구성, 가격 적합성,
편의시설, 이동 거리를 종합적으로 분석합니다.
반드시 데이터에 근거하여 발언하세요.
"""

# ── 통합 분석가 발언 요청 (text 타입, Langfuse: "restaurant-analyst-speak") ──
ANALYST_SPEAK_PROMPT = """\
아래 식당 1곳에 대한 종합 분석을 해주세요.

## 회식 정보
{dining_info}

## 참여자 알레르기
{allergy_info}

## 식당 정보
{restaurant_info}

알레르기 위험, 메뉴 다양성, 가격 적합성, 편의시설, 거리를 종합하여
3~5문장으로 분석해주세요.
"""

# ── 페르소나 반응 (chat 타입, Langfuse: "restaurant-persona-react") ─────────
PERSONA_REACT_CHAT_FALLBACK = [
    {
        "role": "user",
        "content": (
            "분석가 의견:\n{analyst_speech}\n\n"
            "{previous_reactions}"
            "위 분석을 읽고 짧게 반응해주세요. (60자 이내)"
        ),
    }
]

# ── 페르소나 투표 (chat 타입, Langfuse: "restaurant-persona-vote") ──────────
PERSONA_VOTE_CHAT_FALLBACK = [
    {
        "role": "user",
        "content": (
            "분석가 의견:\n{analyst_speech}\n\n"
            "참여자 반응:\n{all_reactions}\n\n"
            "이 식당을 회식 장소로 추천하시겠습니까?\n"
            "반드시 아래 JSON 형식으로만 응답하세요.\n\n"
            '```json\n{{"approve": true/false, "reasoning": "사유 (30자 이내)"}}\n```'
        ),
    }
]
```

---

## Phase 5. 신규 노드

---

### 5-1. `app/nodes/restaurant_dialogue.py`

**신규 작성 — 핵심 노드**

#### 식당 데이터 포맷 함수

```python
def _format_restaurant_info(
    restaurant: Dict[str, Any],
    dining_data: Dict[str, Any],
) -> tuple[str, str]:
    """식당 데이터 전체를 포맷. (restaurant_info, allergy_info) 반환"""
    # restaurant_info: place_name, category_detail, menus (title+price 상위 10개),
    #                  review_keywords (상위 5개), review_count, amenities,
    #                  거리 (x,y vs dining_data의 x,y → math.sqrt 계산)
    # allergy_info: user_data_list의 알레르기 목록 + 메뉴 위험 여부
```

거리 계산: `math.sqrt((x1-x2)**2 + (y1-y2)**2)` (좌표계 거리)

#### 분석가 발언 생성

```python
@observe(as_type="generation")
async def _analyst_speak(restaurant_info: str, dining_info: str, allergy_info: str) -> str:
    llm = get_chat_llm(temperature=0.3, local=False)  # API 모델
    user_prompt, _ = get_prompt(
        "restaurant-analyst-speak",
        ANALYST_SPEAK_PROMPT,
        restaurant_info=restaurant_info,
        dining_info=dining_info,
        allergy_info=allergy_info,
    )
    response = await llm.ainvoke([
        SystemMessage(content=ANALYST_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ])
    return response.content
```

#### 페르소나 반응 생성

```python
@observe(as_type="generation")
async def _persona_react(
    system_prompt: str,
    analyst_speech: str,
    previous_reactions: str,  # "[닉네임]: 내용\n" 누적
) -> str:
    llm = get_chat_llm(temperature=0.7, local=True)  # 로컬 모델
    messages, _ = get_chat_prompt(
        "restaurant-persona-react",
        PERSONA_REACT_CHAT_FALLBACK,
        analyst_speech=analyst_speech,
        previous_reactions=previous_reactions,
    )
    response = await llm.ainvoke([SystemMessage(content=system_prompt)] + messages)
    return response.content
```

#### 페르소나 투표 생성

```python
@observe(as_type="generation")
async def _persona_vote(
    system_prompt: str,
    analyst_speech: str,
    all_reactions: str,  # 전체 반응 합산
) -> dict:
    """{"approve": bool, "reasoning": str} 반환. 파싱 실패 시 approve=False."""
    llm = get_chat_llm(temperature=0.0, local=True)  # 로컬 모델
    messages, _ = get_chat_prompt(
        "restaurant-persona-vote",
        PERSONA_VOTE_CHAT_FALLBACK,
        analyst_speech=analyst_speech,
        all_reactions=all_reactions,
    )
    response = await llm.ainvoke([SystemMessage(content=system_prompt)] + messages)
    return _parse_vote_response(response.content)
```

#### 투표 결과 파싱

```python
def _parse_vote_response(text: str) -> dict:
    """```json ... ``` 블록 또는 raw JSON 파싱. 실패 시 {"approve": False, "reasoning": "파싱 실패"} 반환."""
```

#### 메인 노드 함수

```python
@observe(name="restaurant_dialogue")
async def restaurant_dialogue(state: AgentDialogueState) -> dict:
    restaurant_index = state.get("restaurant_index", 0)
    restaurant = state["candidate_pool"][restaurant_index]
    restaurant_id = str(restaurant["_id"])
    place_name = restaurant["place_name"]

    # 1. 식당 데이터 포맷
    restaurant_info, allergy_info = _format_restaurant_info(restaurant, state["dining_data"])
    dining_info = _format_dining_info(state["dining_data"])

    # 2. 분석가 발언 생성 (API LLM)
    analyst_speech = await _analyst_speak(restaurant_info, dining_info, allergy_info)
    dialogue_history = state.get("dialogue_history", []) + [{
        "type": "analyst",
        "restaurant_id": restaurant_id,
        "place_name": place_name,
        "content": analyst_speech,
    }]

    # 3. 각 페르소나 순차 반응 (로컬 LLM)
    persona_prompts = state["persona_prompts"]
    previous_reactions = ""
    for user_id, system_prompt in persona_prompts.items():
        nickname = _get_nickname(user_id, state["user_data_list"])
        content = await _persona_react(system_prompt, analyst_speech, previous_reactions)
        previous_reactions += f"[{nickname}]: {content}\n"
        dialogue_history.append({
            "type": "reaction",
            "restaurant_id": restaurant_id,
            "user_id": user_id,
            "nickname": nickname,
            "content": content,
        })

    # 4. 각 페르소나 투표 (로컬 LLM)
    all_reactions = previous_reactions
    vote_results = []
    for user_id, system_prompt in persona_prompts.items():
        nickname = _get_nickname(user_id, state["user_data_list"])
        vote = await _persona_vote(system_prompt, analyst_speech, all_reactions)
        vote_results.append({
            "user_id": user_id,
            "nickname": nickname,
            **vote,
        })
        dialogue_history.append({
            "type": "vote",
            "restaurant_id": restaurant_id,
            "user_id": user_id,
            "nickname": nickname,
            "approve": vote["approve"],
            "reasoning": vote["reasoning"],
        })

    # 5. 과반수 판정
    approve_count = sum(1 for v in vote_results if v["approve"])
    total_count = len(vote_results)
    recommended = state.get("recommended_restaurants", [])
    if approve_count > total_count / 2:
        recommended = recommended + [{
            "restaurant_id": restaurant_id,
            "place_name": place_name,
        }]

    # 6. processed_restaurants 누적
    processed = state.get("processed_restaurants", []) + [{
        "restaurant_id": restaurant_id,
        "place_name": place_name,
        "approve_count": approve_count,
        "total_count": total_count,
        "score": restaurant.get("score", 0),
    }]

    # 7. persona_votes 누적
    persona_votes = state.get("persona_votes", []) + vote_results

    return {
        "restaurant_index": restaurant_index + 1,
        "dialogue_history": dialogue_history,
        "recommended_restaurants": recommended,
        "processed_restaurants": processed,
        "persona_votes": persona_votes,
    }
```

---

## Phase 6. 진입점

---

### 6-1. `app/main.py`

**원본:** `iterative_discussion/app/main.py`
**변경:**
- import 경로 전체 변경
- `build_consensus_graph()` → `build_agent_dialogue_graph()`
- `create_initial_state()` 파라미터: `max_rounds`/`min_rounds` 제거
- `final_selection` 결정 로직:
  ```python
  recommended = state.get("recommended_restaurants", [])
  if len(recommended) < 5:
      # fallback: processed_restaurants를 approve_count 내림차순 → score 내림차순 정렬
      # recommended에 없는 것 중 부족분 추가
      already_ids = {r["restaurant_id"] for r in recommended}
      extras = sorted(
          [r for r in state.get("processed_restaurants", []) if r["restaurant_id"] not in already_ids],
          key=lambda r: (r["approve_count"], r["score"]),
          reverse=True,
      )
      recommended = recommended + extras[: 5 - len(recommended)]
  final_selection = recommended[:5]
  ```
- streaming 콜백: `type == "analyst"` → `user_id=0`으로 발행
- `_save_persona_votes()`: restaurant-centric `persona_votes` → user-centric 변환 후 DB 저장
  ```python
  # restaurant-centric: [{user_id, nickname, approve, reasoning, restaurant_id?}, ...]
  # user-centric: {user_id: [{restaurant_id, approve, reasoning}, ...]}
  ```

---

### 6-2. `streamlit_app.py`

**원본:** `iterative_discussion/streamlit_app.py`
**변경:**

| 항목 | 변경 내용 |
|---|---|
| import 경로 | `agent_dialogue`로 변경 |
| mock 경로 | `agent_dialogue.app.nodes.persona_factory.DBManager` |
| 사이드바 파라미터 | `max_rounds`/`min_rounds` 파라미터 제거 |
| 노드 렌더링 | `restaurant_dialogue`: 분석가 발언 `st.info()`, 페르소나 반응 `chat_message()`, 투표 결과 `st.success`/`st.warning` |
| 최종 결과 | `recommended_restaurants` 테이블 (5개, fallback 포함) |
| `on_persona_speak` | `type == "analyst"`이면 `st.info(f"🔍 [{place_name}]: {content}")` |

---

## 구현 순서 요약

```
Phase 1  __init__.py × 6
         utils/logging_config.py     (복사)
         utils/monitoring.py         (복사 + 함수명 변경)
         utils/scoring.py            (복사)
         engine/llm_factory.py       (복사)
         prompts/langfuse_prompts.py (복사)
         prompts/persona_templates.py (복사)

Phase 2  engine/state.py             (신규)
         engine/graph.py             (신규)

Phase 3  nodes/persona_factory.py    (import 변경 + self_evolution 통합)
         nodes/moderator_preselect.py (import 변경 + batch/offset 추가)

Phase 4  prompts/restaurant_templates.py (신규)

Phase 5  nodes/restaurant_dialogue.py   (신규 — 핵심)

Phase 6  app/main.py       (수정)
         streamlit_app.py  (수정)
```

총 파일 수: 16개 (신규 4 / 복사 6 / 수정 3 / 진입점 3)
