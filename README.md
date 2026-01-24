# Restaurant Service - AI Backend

LangGraph 기반의 멀티 기능 AI 백엔드 서비스입니다.


## 📁 프로젝트 구조

```
project-root/
├── src/               # 소스 코드
├── tests/            # 테스트 코드
├── docs/             # 문서
├── scripts/          # 유틸리티 스크립트
└── ...
```

## 🏗️ 아키텍처 설계

### Source Code Structure (`src/`)

```
src/
├── features/                    # 기능별 독립 모듈
│   ├── recommendation/          # 추천 시스템
│   │   ├── api/                # REST API 엔드포인트
│   │   ├── graphs/             # LangGraph 워크플로우
│   │   │   ├── nodes/          # 그래프 노드 (처리 단위)
│   │   │   └── states/         # 상태 정의 (TypedDict)
│   │   ├── services/           # 비즈니스 로직
│   │   ├── repositories/       # 데이터 액세스 계층
│   │   ├── tools/              # LLM이 사용할 도구들
│   │   └── models/             # 데이터 모델
│   │       ├── domain.py       # 도메인 모델
│   │       └── schemas.py      # API 스키마 (Pydantic)
│   │
│   └── ocr/                    # OCR 파이프라인
│       ├── api/
│       ├── graphs/
│       ├── services/
│       ├── repositories/
│       ├── tools/
│       └── models/
│
├── shared/                     # 공통 모듈
│   ├── llm/                    # LLM 공통
│   │   ├── providers/          # LLM 프로바이더 (OpenAI, Anthropic 등)
│   │   └── prompts/            # 공통 프롬프트 템플릿
│   ├── database/               # 데이터베이스 연결 및 세션 관리
│   ├── cache/                  # Redis 등 캐시 클라이언트
│   ├── utils/                  # 유틸리티 함수들
│   └── exceptions.py           # 공통 예외 정의
│
├── core/                       # 앱 전체 설정
│   ├── config.py               # 환경 변수 및 설정 관리
│   ├── logging.py              # 로깅 설정
│   ├── security.py             # 인증/권한 관리
│   └── dependencies.py         # FastAPI 의존성 주입
│
└── main.py                     # FastAPI 진입점
```

#### Features (기능 모듈)

각 기능은 완전히 독립된 모듈로 구성되어 있으며, 필요시 마이크로서비스로 쉽게 분리할 수 있습니다.

**📍 recommendation/ - 회식 추천 시스템**

주요 컴포넌트:
- `graphs/recommendation_graph.py`: 추천 워크플로우 정의
- `nodes/intent_analyzer.py`: 사용자 의도 분석 노드
- `nodes/restaurant_searcher.py`: 식당 검색 노드
- `nodes/recommendation_generator.py`: 추천 생성 노드
- `tools/restaurant_search.py`: 식당 검색 도구
- `tools/map_integration.py`: 지도 API 연동

**🔍 ocr/ - OCR 파이프라인**

주요 컴포넌트:
- `graphs/ocr_graph.py`: OCR 워크플로우 정의
- `nodes/image_preprocessor.py`: 이미지 전처리 노드
- `nodes/text_extractor.py`: 텍스트 추출 노드
- `nodes/result_validator.py`: 결과 검증 노드
- `tools/vision_api.py`: Vision API 연동

#### Shared (공통 모듈)

여러 기능에서 공통으로 사용하는 코드를 모아둔 레이어입니다.

주요 컴포넌트:
- `llm/providers/base_provider.py`: LLM 프로바이더 인터페이스
- `llm/providers/openai_provider.py`: OpenAI 연동
- `database/base.py`: SQLAlchemy Base 모델
- `database/session.py`: DB 세션 관리

#### Core (전역 설정)

애플리케이션 전체에 영향을 미치는 설정 및 초기화 코드입니다.

### Test Structure (`tests/`)

```
tests/
├── unit/                           # 단위 테스트 (가장 많음)
│   ├── features/
│   │   ├── recommendation/
│   │   │   ├── graphs/
│   │   │   │   ├── nodes/
│   │   │   │   │   ├── test_intent_analyzer.py
│   │   │   │   │   ├── test_restaurant_searcher.py
│   │   │   │   │   └── test_recommendation_generator.py
│   │   │   │   └── states/
│   │   │   │       └── test_recommendation_state.py
│   │   │   ├── services/
│   │   │   │   ├── test_restaurant_service.py
│   │   │   │   └── test_scoring_service.py
│   │   │   ├── repositories/
│   │   │   │   └── test_restaurant_repository.py
│   │   │   ├── tools/
│   │   │   │   ├── test_restaurant_search.py
│   │   │   │   └── test_map_integration.py
│   │   │   └── models/
│   │   │       ├── test_domain.py
│   │   │       └── test_schemas.py
│   │   │
│   │   └── ocr/
│   │       ├── graphs/
│   │       │   └── nodes/
│   │       │       ├── test_image_preprocessor.py
│   │       │       ├── test_text_extractor.py
│   │       │       └── test_result_validator.py
│   │       ├── services/
│   │       ├── repositories/
│   │       └── tools/
│   │
│   └── shared/
│       ├── llm/
│       │   ├── providers/
│       │   │   ├── test_base_provider.py
│       │   │   ├── test_openai_provider.py
│       │   │   └── test_anthropic_provider.py
│       │   └── prompts/
│       ├── database/
│       ├── cache/
│       └── utils/
│
├── integration/                    # 통합 테스트 (중간)
│   ├── features/
│   │   ├── recommendation/
│   │   │   ├── test_recommendation_graph.py      # 그래프 전체 흐름
│   │   │   ├── test_api_endpoints.py             # API 통합
│   │   │   └── test_end_to_end_flow.py           # Feature 전체 흐름
│   │   │
│   │   └── ocr/
│   │       ├── test_ocr_graph.py
│   │       ├── test_api_endpoints.py
│   │       └── test_end_to_end_flow.py
│   │
│   ├── shared/
│   │   ├── test_database_integration.py
│   │   └── test_cache_integration.py
│   │
│   └── cross_feature/                            # 기능 간 통합
│       └── test_feature_interactions.py
│
├── e2e/                            # E2E 테스트 (소수)
│   ├── test_recommendation_user_journey.py       # 사용자 여정 테스트
│   ├── test_ocr_user_journey.py
│   └── test_full_system.py                       # 전체 시스템
│
├── performance/                    # 성능 테스트
│   ├── test_recommendation_performance.py
│   ├── test_ocr_performance.py
│   └── test_load.py
│
├── fixtures/                       # 공통 Fixture
│   ├── recommendation_fixtures.py
│   ├── ocr_fixtures.py
│   ├── database_fixtures.py
│   └── llm_fixtures.py
│
├── data/                           # 테스트 데이터
│   ├── mock_restaurants.py
│   ├── mock_images.py
│   ├── sample_responses.json
│   └── test_images/
│       ├── sample1.png
│       └── sample2.jpg
│
├── conftest.py                     # pytest 전역 설정
└── pytest.ini                      # pytest 설정 파일
```

#### 테스트 레이어 설명

**🔬 Unit Tests (단위 테스트)**
- **목적**: 개별 함수, 클래스, 메서드의 동작 검증
- **특징**: 
  - 외부 의존성은 Mock 처리
  - 실행 속도 빠름
  - 가장 많은 수의 테스트
- **테스트 대상**:
  - 각 노드 함수의 로직
  - 서비스 레이어의 비즈니스 로직
  - 리포지토리의 데이터 액세스
  - 유틸리티 함수
  - LLM 호출은 Mock 처리

**🔗 Integration Tests (통합 테스트)**
- **목적**: 여러 컴포넌트 간의 상호작용 검증
- **특징**:
  - 실제 DB 연결 (테스트 DB)
  - 일부 외부 서비스는 Mock
  - 중간 정도의 실행 속도
- **테스트 대상**:
  - LangGraph 노드 간 상태 전이
  - API → Graph → Service 흐름
  - 데이터베이스 연동
  - 캐시 동작

**🎯 E2E Tests (End-to-End 테스트)**
- **목적**: 실제 사용자 시나리오 검증
- **특징**:
  - 전체 시스템 통합
  - 실제 환경과 유사
  - 실행 속도 느림
  - 소수의 중요한 시나리오만
- **테스트 대상**:
  - 사용자 여정 (User Journey)
  - 전체 추천 플로우
  - 전체 OCR 파이프라인

**⚡ Performance Tests (성능 테스트)**
- **목적**: 성능 지표 측정 및 병목 지점 파악
- **테스트 대상**:
  - 응답 시간
  - 처리량 (Throughput)
  - 동시 요청 처리

#### 테스트 지원 파일

**📦 fixtures/**
- 재사용 가능한 테스트 데이터 및 Mock 객체
- Feature별로 분리된 fixture 파일
- 공통 fixture (DB, LLM, API 클라이언트 등)

**📊 data/**
- Mock 데이터 (레스토랑, 이미지 등)
- 샘플 응답 JSON
- 테스트용 이미지 파일

**⚙️ conftest.py**
- pytest 전역 설정
- 모든 테스트에서 사용 가능한 fixture 정의
- 테스트 마커 설정

**🔧 pytest.ini**
- pytest 설정 파일
- 테스트 경로, 옵션, 마커 정의

## 🔄 데이터 흐름

### 1. API 요청 처리 흐름
```
Client Request
    ↓
FastAPI Route (features/*/api/routes.py)
    ↓
LangGraph Workflow (features/*/graphs/*_graph.py)
    ↓
Nodes → Services → Repositories → Database/External APIs
    ↓
Response
```

### 2. LangGraph 워크플로우 구조
```
State (입력 데이터)
    ↓
Node 1 (처리) → State 업데이트
    ↓
Node 2 (처리) → State 업데이트
    ↓
Node N (처리) → State 업데이트
    ↓
Final State (출력 데이터)
```

### 3. 테스트 피라미드
```
        ┌─────────────┐
        │  E2E Tests  │  ← 전체 시스템 (소수, 느림)
        └─────────────┘
       ┌───────────────┐
       │ Integration   │   ← 컴포넌트 통합 (중간)
       └───────────────┘
     ┌─────────────────┐
     │   Unit Tests    │    ← 개별 단위 (다수, 빠름)
     └─────────────────┘
```

## 🎯 설계 원칙

### 1. 관심사의 분리 (Separation of Concerns)
- 각 계층은 명확한 책임을 가짐
- API, 비즈니스 로직, 데이터 액세스를 분리

### 2. 기능별 모듈화 (Feature-based Modularity)
- 각 기능은 독립적으로 개발/배포/테스트 가능
- 기능 간 결합도 최소화

### 3. 의존성 방향 (Dependency Direction)
```
API → Graphs → Services → Repositories → Database
 ↓       ↓        ↓
Shared Modules (llm, cache, utils)
```

### 4. 확장성 (Scalability)
- 새로운 기능 추가 시 `features/` 아래 새 폴더 생성
- 새로운 LLM 프로바이더 추가 시 `shared/llm/providers/` 확장
- 마이크로서비스 전환 시 각 feature를 독립 서비스로 분리 가능

### 5. 테스트 주도 개발 (TDD)
- 테스트 먼저 작성 (Red)
- 최소 구현 (Green)
- 리팩토링 (Refactor)
- 높은 테스트 커버리지 유지

## 📦 주요 기술 스택

- **Framework**: FastAPI
- **AI Orchestration**: LangGraph
- **LLM**: OpenAI GPT
- **Database**: 미정
- **Cache**: 미정
- **Testing**: pytest, pytest-cov, pytest-asyncio
- **Dependency Management**: Poetry

## 🚀 시작하기

### 환경 설정
우선 poetry로 작성 변경 시 추후 수정 예정

```bash
# 의존성 설치
poetry install

# 환경 변수 설정
cp .env.example .env
# .env 파일 수정

# 개발 서버 실행
poetry run uvicorn src.main:app --reload
```

### API 문서

서버 실행 후 다음 URL에서 API 문서 확인:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 테스트 실행

### 전체 테스트
```bash
# 모든 테스트 실행 (expensive 테스트 제외)
poetry run pytest

# 커버리지 포함 실행
poetry run pytest --cov=src --cov-report=html
```

### 레벨별 테스트
```bash
# 단위 테스트만
poetry run pytest tests/unit -v

# 통합 테스트만
poetry run pytest tests/integration -v

# E2E 테스트만
poetry run pytest tests/e2e -v

# 특정 기능만
poetry run pytest tests/unit/features/recommendation -v
```

### 마커별 테스트
```bash
# 빠른 테스트만 (expensive 제외)
poetry run pytest -m "not expensive"

# 느린 테스트 포함
poetry run pytest -m "slow"

# 실제 LLM API 호출하는 테스트 (비용 발생!)
poetry run pytest -m "expensive"

# 통합 테스트만
poetry run pytest -m "integration"
```

### 테스트 마커 종류

| 마커 | 설명 | 사용 예시 |
|------|------|----------|
| `unit` | 단위 테스트 | `@pytest.mark.unit` |
| `integration` | 통합 테스트 | `@pytest.mark.integration` |
| `e2e` | E2E 테스트 | `@pytest.mark.e2e` |
| `slow` | 느린 테스트 (>1초) | `@pytest.mark.slow` |
| `expensive` | 실제 LLM API 호출 (비용 발생) | `@pytest.mark.expensive` |

## 📝 개발 가이드

### 새로운 기능 추가

1. `src/features/` 아래 새 폴더 생성
2. 기본 구조 복사 (api, graphs, services, repositories, tools, models)
3. `tests/unit/features/` 아래 대응하는 테스트 폴더 생성
4. **TDD 방식으로 개발**:
   - 테스트 먼저 작성
   - 최소 구현
   - 리팩토링
5. LangGraph 워크플로우 정의
6. API 라우트 추가
7. `src/main.py`에 라우터 등록

### TDD 개발 사이클

```
1. 🔴 Red: 실패하는 테스트 작성
    ↓
2. 🟢 Green: 테스트를 통과하는 최소 코드 작성
    ↓
3. 🔵 Refactor: 코드 개선 및 정리
    ↓
   반복
```

### LangGraph 노드 작성 규칙

```python
from typing import TypedDict

# 1. State 정의
class MyState(TypedDict):
    input_data: str
    result: str

# 2. 테스트 먼저 작성
def test_my_node():
    state = MyState(input_data="test", result="")
    result = my_node(state)
    assert result["result"] == "expected"

# 3. Node 함수 작성
def my_node(state: MyState) -> MyState:
    result = process(state["input_data"])
    return {**state, "result": result}

# 4. Graph에 노드 추가
from langgraph.graph import StateGraph

graph = StateGraph(MyState)
graph.add_node("my_node", my_node)
```

### 테스트 작성 가이드

#### 1. 파일 구조 미러링
```
src/features/recommendation/services/restaurant_service.py
  ↓ 대응
tests/unit/features/recommendation/services/test_restaurant_service.py
```

#### 2. 테스트 네이밍 규칙
```python
# 파일명: test_{원본파일명}.py
# 클래스명: Test{클래스명}
# 함수명: test_{테스트하려는_동작}

class TestRestaurantService:
    def test_search_by_location_success(self):
        pass
    
    def test_search_with_invalid_location(self):
        pass
```

#### 3. Given-When-Then 패턴
```python
def test_search_restaurants():
    # Given (준비)
    state = RecommendationState(location="강남역")
    
    # When (실행)
    result = search_restaurants(state)
    
    # Then (검증)
    assert len(result["restaurants"]) > 0
```

#### 4. Mock 사용
```python
# LLM 호출은 항상 Mock 처리 (단위 테스트)
def test_intent_analyzer_with_mock_llm(mock_llm):
    mock_llm.invoke.return_value = "이탈리안"
    
    analyzer = IntentAnalyzer(llm=mock_llm)
    result = analyzer.analyze("파스타 먹고싶어")
    
    assert result["cuisine_type"] == "이탈리안"
    mock_llm.invoke.assert_called_once()
```

#### 5. Fixture 활용
```python
# conftest.py 또는 fixtures/ 파일에 정의
@pytest.fixture
def base_state():
    return RecommendationState(
        user_input="테스트",
        location="강남역",
        restaurants=[]
    )

# 테스트에서 사용
def test_something(base_state):
    result = process(base_state)
    assert result is not None
```

### 계층별 책임

| 계층 | 책임 | 예시 | 테스트 위치 |
|------|------|------|-------------|
| **API** | HTTP 요청/응답 처리 | 라우팅, 검증, 직렬화 | `tests/unit/features/*/api/` |
| **Graphs** | AI 워크플로우 오케스트레이션 | 노드 연결, 상태 관리 | `tests/unit/features/*/graphs/` |
| **Services** | 비즈니스 로직 | 필터링, 점수 계산 | `tests/unit/features/*/services/` |
| **Repositories** | 데이터 액세스 | DB 쿼리, 캐시 조회 | `tests/unit/features/*/repositories/` |
| **Tools** | LLM 도구 | 외부 API 호출 | `tests/unit/features/*/tools/` |
| **Models** | 데이터 구조 정의 | 도메인 모델, 스키마 | `tests/unit/features/*/models/` |

### 테스트 커버리지 목표

- **전체 커버리지**: 80% 이상
- **핵심 비즈니스 로직**: 90% 이상
- **유틸리티/헬퍼**: 70% 이상

## 📚 참고 문서

- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [pytest 공식 문서](https://docs.pytest.org/)
- 내부 아키텍처 문서: `docs/architecture.md`
- API 스펙: `docs/api_specs.md`

## 🤝 기여 가이드

1. Feature 브랜치 생성 (`git checkout -b feature/amazing-feature`)
2. **TDD로 개발**: 테스트 먼저 작성 → 구현 → 리팩토링
3. 테스트 실행 및 커버리지 확인 (`pytest --cov=src`)
4. 변경사항 커밋 (`git commit -m 'Add some amazing feature'`)
5. 브랜치에 푸시 (`git push origin feature/amazing-feature`)
6. Pull Request 생성

### PR 체크리스트
- [ ] 모든 테스트 통과
- [ ] 커버리지 80% 이상 유지
- [ ] 새로운 기능에 대한 테스트 작성
- [ ] 문서 업데이트 (필요시)


