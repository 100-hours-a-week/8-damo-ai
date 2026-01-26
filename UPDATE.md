# AI Pipeline 향후 최적화 및 개선 과제

이 문서는 추천 시스템 및 LangGraph 파이프라인의 효율성을 높이기 위해 향후 검토 및 적용해야 할 사항들을 정리합니다.

---

## 1. 구조적 최적화 (Architecture)

### 1.1 요청 모델 통합 및 상속
`RecommendationRequest`와 `AnalyzeRefreshRequest`를 별도로 관리하기보다 상속 구조를 활용하여 공통 로직을 최소화합니다.
- **적용 방향**: `AnalyzeRefreshRequest`가 `RecommendationRequest`를 상속받고 `refresh_count`, `excluded_restaurant_ids` 등의 필드를 추가.

### 1.2 LangGraph 조건부 엣지 (Conditional Edges) 활용
`is_refresh` 상태값에 따라 불필요한 노드 실행을 건너뛰는 흐름을 구축합니다.
- **예시**: `is_refresh=True`일 경우 무거운 분석 노드를 건너뛰고 기존 후보군에서 필터링하는 노드로 직접 이동.

---

## 2. 성능 및 비즈니스 로직 최적화 (Performance)

### 2.1 추천 후보군 데이터 캐싱 (Caching)
- **일반 추천 (is_refresh=False)**: LLM 분석 및 벡터 검색 결과(예: 상위 50개 리스트)를 캐시(Redis 등)에 저장.
- **재추천 (is_refresh=True)**: 다시 분석하지 않고 캐시된 리스트에서 `excluded_restaurant_ids`만 제외하고 즉시 반환 (응답 속도 획기적 개선).

### 2.2 Re-rank 및 검색 범위 유동화
- `refresh_count`가 늘어남에 따라(예: 3회 이상) 검색 반경(`Radius`)을 넓히거나 추천 가중치를 변경하는 전략 노드 추가.

---

## 3. 코드 수준 개선 (Code Quality)

### 3.1 유효성 검사 로직 단일화
- `routes_v1.py`에서 반복되는 `dining_data`, `user_data` 비어있음 체크 로직을 Pydantic의 `@model_validator`나 공통 유효성 검사 유틸리티로 이관.

### 3.2 State 필드 확장
- `RecommendationState`에 `excluded_restaurant_ids: List[str]` 필드를 추가하여, 재추천 시 이전에 노출된 식당이 중복되지 않도록 보장.

---

## 4. 기타 검토 사항
- 백엔드와 상의하여 추천 식당 정보 응답 시의 책임 소재(필드 구성) 확정.
- Snowflake ID(int)와 통신용 문자열(str) 사이의 타입 정합성 상시 체크.
