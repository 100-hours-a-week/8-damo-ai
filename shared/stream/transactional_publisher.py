"""Kafka 트랜잭셔널 프로듀서 래퍼.

exactly-once 의미론(EOS)을 위해 aiokafka의 트랜잭셔널 API를 사용한다.

동작 방식:
  1. enable_idempotence=True  → 프로듀서 재시도 시 중복 메시지 방지
  2. transactional_id        → 브로커가 동일 프로듀서 세션을 식별
  3. send_offsets_to_transaction → 컨슈머 오프셋을 프로듀스와 원자적으로 커밋

  consume → process → produce → commit offset  이 네 단계가 하나의 Kafka 트랜잭션으로 묶인다.
  중간에 프로세스가 죽으면 트랜잭션이 롤백되고, 컨슈머가 재시작 시 같은 메시지를 재처리한다.
  (LangGraph 체크포인터와 결합 시 파이프라인은 중단 지점부터 재개)

주의:
  - 단일 트랜잭셔널 프로듀서 인스턴스는 동시에 하나의 트랜잭션만 열 수 있다.
    → asyncio.Lock으로 직렬화하되, 파이프라인 실행 중이 아닌 발행 시점에만 락을 유지한다.
  - 컨슈머 측에서는 enable_auto_commit=False 와 isolation_level=read_committed 설정 필요.
"""
import asyncio
import json
import logging
from typing import Any

from aiokafka import AIOKafkaProducer
from aiokafka.structs import TopicPartition

logger = logging.getLogger(__name__)


class TransactionalPublisher:
    """aiokafka 트랜잭셔널 프로듀서 싱글톤.

    앱 시작 시 start(), 종료 시 stop()을 호출한다.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        transactional_id: str,
        group_id: str,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._transactional_id = transactional_id
        self._group_id = group_id
        self._producer: AIOKafkaProducer | None = None
        self._lock: asyncio.Lock | None = None  # start() 에서 이벤트 루프 바인딩

    async def start(self) -> None:
        """프로듀서를 시작하고 트랜잭션을 초기화한다."""
        # Lock을 실행 중인 이벤트 루프에서 생성 (Python <3.10 호환)
        self._lock = asyncio.Lock()
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            enable_idempotence=True,
            transactional_id=self._transactional_id,
        )
        await self._producer.start()
        await self._producer.init_transactions()
        logger.info(
            "TransactionalPublisher 시작: transactional_id=%s", self._transactional_id
        )

    async def stop(self) -> None:
        """프로듀서를 종료한다."""
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
            logger.info("TransactionalPublisher 종료")

    async def publish(
        self,
        topic: str,
        value: Any,
        key: bytes | None = None,
        headers: list[tuple[str, bytes]] | None = None,
        consumer_topic: str | None = None,
        consumer_partition: int | None = None,
        consumer_offset: int | None = None,
    ) -> None:
        """메시지를 트랜잭션 내에서 발행하고 컨슈머 오프셋을 원자적으로 커밋한다.

        Args:
            topic: 발행할 Kafka 토픽
            value: 발행할 메시지 (Pydantic 모델, dict, str, bytes 모두 가능)
            key: 메시지 키 (파티셔닝용)
            headers: 메시지 헤더 목록
            consumer_topic: 오프셋을 커밋할 컨슈머 토픽 (exactly-once 필요 시)
            consumer_partition: 오프셋을 커밋할 파티션 번호
            consumer_offset: 처리 완료한 오프셋 (커밋 시 +1 됨)
        """
        if self._producer is None or self._lock is None:
            raise RuntimeError("TransactionalPublisher가 시작되지 않았습니다. start()를 먼저 호출하세요.")

        encoded = _encode(value)
        can_commit_offset = (
            consumer_topic is not None
            and consumer_partition is not None
            and consumer_offset is not None
        )

        async with self._lock:
            async with self._producer.transaction():
                await self._producer.send(
                    topic,
                    value=encoded,
                    key=key,
                    headers=headers or [],
                )

                if can_commit_offset:
                    # 컨슈머 오프셋을 프로듀스와 동일한 트랜잭션으로 커밋
                    # → 이 트랜잭션이 롤백되면 오프셋도 롤백됨 (exactly-once)
                    tp = TopicPartition(consumer_topic, consumer_partition)
                    await self._producer.send_offsets_to_transaction(
                        {tp: consumer_offset + 1},  # 다음에 읽을 오프셋
                        self._group_id,
                    )
                    logger.debug(
                        "오프셋 커밋 포함 트랜잭션 완료: topic=%s partition=%d offset=%d→%d",
                        consumer_topic,
                        consumer_partition,
                        consumer_offset,
                        consumer_offset + 1,
                    )

        logger.debug(
            "트랜잭셔널 발행 완료: topic=%s, key=%s",
            topic,
            key.decode("utf-8", errors="ignore") if key else None,
        )


def _encode(value: Any) -> bytes:
    """메시지를 bytes로 직렬화한다."""
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    try:
        if hasattr(value, "model_dump"):
            return json.dumps(value.model_dump(), ensure_ascii=False).encode("utf-8")
        return json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"메시지 직렬화 실패: {type(value).__name__}"
        ) from exc


# 모듈 레벨 싱글톤
_publisher: TransactionalPublisher | None = None


def get_transactional_publisher() -> TransactionalPublisher | None:
    return _publisher


def set_transactional_publisher(publisher: TransactionalPublisher) -> None:
    global _publisher
    _publisher = publisher
