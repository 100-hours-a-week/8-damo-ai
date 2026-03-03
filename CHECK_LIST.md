# Kafka Integration Test Checklist (v2-gateway)

V2-Gateway와 AI 엔진 간의 Kafka 통신 및 로직 정합성을 검증하기 위한 체크리스트입니다.

## 1. 공통 인프라 체크 (Common)
- [x] **RunPod Connectivity**: `RunPodClient.health_check()`가 정상적으로 200 OK를 반환하는가?
- [x] **Kafka Connectivity**: `settings.KAFKA_BOOTSTRAP_SERVERS`에 정상적으로 연결되는가? (Broker 연결 로그 확인)
- [ ] **Correlation ID Tracking**: 모든 로그와 메시지에 `correlation_id`가 포함되어 전달되는가?
- [x] **Error Handling**: `ExceptionMiddleware`가 에러 발생 시 로그를 남기고 프로세스를 유지하는가?

## 2. 회식 추천 흐름 (RECOMMENDATION_REQUEST)
- [x] **Input Parsing**: `RecommendationRequestPayload` (EventId, EventType, Payload) 파싱이 정상적으로 수행되는가?
- [x] **Graph Internal Logic**: 
    - [x] `START -> distance -> budget -> END` 순으로 노드가 실행되는가?
    - [x] `total_score` 기반으로 식당 리스트가 정렬되어 `final_state`에 저장되는가?
- [x] **Data Transformation**: 
    - [x] `final_state`에서 `filtered_restaurant` (List[dict])가 정상 추출되는가?
    - [x] `restaurant_ids` (List[str])로의 ID 추출 가공이 올바른가? (Pydantic 에러 유무)
- [x] **Outbound Event**: `discussion-request` 토픽으로 결과가 발행되는가?

## 3. 회식 재추천 흐름 (RECOMMENDATION_REFRESH_REQUEST)
- [ ] **Vote Result Mapping**: 유저가 이전에 보낸 `vote_result_list`가 AI 토론 요청 페이로드로 정확히 전달되는가? (매핑 확인)
- [ ] **Graph Refresh logic**: `type='refresh'` 파라미터가 그래프 태스크에 정상 전달되는가?
- [ ] **Resource Management**: `await runpod.close()`가 성공적으로 호출되어 좀비 프로세스를 방지하는가?

## 4. AI 토론 응답 처리 (DISCUSSION_RESPONSE)
- [ ] **Phase Counting**: DB(`dining_sessions`)의 `currentPhase` 값이 1 증가하는가?
- [ ] **Schema Mapping**: AI 응답의 `summary`가 `reasoning_description` 필드로 정상 매핑되는가?
- [ ] **BE Notification**: `recommendation-response` 토픽으로 백엔드용 최종 결과가 발행되는가?

## 5. 데이터 정합성 (Data Integrity)
- [ ] **ID Consistency**: MongoDB `_id` (ObjectId)가 Kafka 전송 시 문자열(`str`)로 정상 직렬화되는가?
- [ ] **CamelCase vs snake_case**: Pydantic의 `BaseSchema` 설정에 따라 JSON 키값이 CamelCase로 정확히 변환되는가?

---

### 🚀 테스트 실행 가이드 (로컬)
1.  **로컬 테스트 모드 활용**: `diningData.x = "DAMO_TEST"`인 메시지를 발행하여 `task.py`의 목업 데이터가 AI 토론 요청으로 이어지는지 확인.
2.  **모니터링 도구**: `Langfuse` 대시보드에서 `correlation_id`를 검색하여 전체 트레이스(Trace) 확인.
3.  **로그 확인**: `FastStream`의 `Logger`를 통해 토픽 수신/발행 성공 로그 확인.
