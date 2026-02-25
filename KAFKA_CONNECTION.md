# Kafka Connection Guide (v2-gateway)

이 문서는 `v2-gateway` 프로젝트에서 Kafka를 사용하여 메시지를 송수신하는 방법과 구조를 설명합니다. 이 프로젝트는 **FastStream** 프레임워크를 사용하여 Kafka 통신을 추상화합니다.

## 1. 주요 구성 요소

### 1.1 KafkaService (`shared/stream/service.py`)
카프카 연결 및 공통 로직을 담고 있는 클래스입니다.
- **Broker 설정**: `shared/utils/config.py`의 설정을 기반으로 `KafkaBroker`를 생성합니다.
- **Publisher 관리**: 응답을 보내기 위한 Publisher를 미리 정의하여 재사용합니다.
- **Error Handling**: `ExceptionMiddleware`를 통해 메시지 처리 중 발생하는 예외를 통합 관리합니다.

### 1.2 main.py (`gateway/main.py`)
실제 애플리케이션의 엔트리 포인트이며, 메시지 구독(Subscribe) 및 처리 로직을 담당합니다.
- `KafkaService` 인스턴스를 생성하여 내부의 `broker`를 `FastStream` 앱에 연결합니다.
- `@broker.subscriber()` 데코레이터를 사용하여 특정 토픽의 메시지를 처리합니다.

---

## 2. 사용 방법

### 2.1 환경 변수 설정 (`.env`)
Kafka 연결을 위해 아래 변수들이 설정되어 있어야 합니다.
```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
# 기타 필요한 변수들 (MONGODB_URI, API_KEY 등)
```

### 2.2 메시지 구독하기 (Subscribe)
새로운 이벤트를 수신하려면 `main.py`에 구독 로직을 추가합니다. 토픽 이름은 `service.get_..._topic()` 메서드를 통해 가져오는 것을 권장합니다.

```python
@broker.subscriber(service.get_recommendation_request_topic())
async def handle_recommendation(event: RecommendationRequestPayload, message = Context()):
    # 1. 메시지 수신 확인
    print(f"Received event: {event.event_id}")
    
    # 2. 비즈니스 로직 수행
    # ...
    
    # 3. 필요 시 결과 발행 (Publish)
    # await service.publish_recommendation(...)
```

### 2.3 메시지 발행하기 (Publish)
메시지를 보내려면 `KafkaService`에 정의된 메서드를 호출합니다. 현재 추천 결과 응답을 위한 `publish_recommendation_response`와 추천 결과 스트리밍을 위한 `publish_recommendation_streaming`이 구현되어 있습니다.

```python
# KafkaService 내부 메서드 예시
await service.publish_recommendation_response(
    key=message_key, 
    data=response_data
)

await service.publish_recommendation_streaming(
    key=message_key, 
    data=response_data
)
```

---
