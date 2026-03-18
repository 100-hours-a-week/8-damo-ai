# agent_dialogue RAG 구현 계획

설계 기준: RAG_PLAN.md 참조
구현 순서는 의존성 기준으로 정렬.

---

## 변경 파일 목록

```
신규
  services/agent_dialogue/app/utils/rag.py          벡터 스토어 클라이언트
  services/agent_dialogue/scripts/index_reviews.py  MongoDB → Pinecone 인덱싱

수정
  services/agent_dialogue/app/nodes/restaurant_dialogue.py  retrieve 통합
  services/agent_dialogue/requirements.txt                   pinecone 의존성 추가
  services/agent_dialogue/Dockerfile.runpod                  동일
  shared/utils/config.py                                     환경변수 2개 추가
```

---

## Step 1. 환경변수 추가 (`shared/utils/config.py`)

```python
# 기존 필드에 추가
PINECONE_API_KEY: str = ""
PINECONE_INDEX_NAME: str = "damo-reviews"
```

둘 다 기본값 `""` — Pinecone 미설정 시 RAG는 graceful skip.

---

## Step 2. 의존성 추가 (`services/agent_dialogue/requirements.txt`)

```
langgraph>=0.2.0
langchain-openai>=0.3.0
langchain-core>=0.3.0
pinecone>=5.0.0
```

---

## Step 3. 벡터 스토어 클라이언트 (`app/utils/rag.py`)

### 설계 원칙

- `VectorStore` Protocol로 인터페이스 추상화 → Pinecone → Qdrant 교체 시 `restaurant_dialogue.py` 무수정
- 모든 외부 호출은 `try/except`로 감싸 RAG 실패가 분석 흐름을 막지 않도록 처리
- 클라이언트 인스턴스는 모듈 레벨 싱글톤 (`_store`) 으로 유지

```python
import logging
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from shared.utils.config import settings

logger = logging.getLogger(__name__)


# ── 인터페이스 ─────────────────────────────────────────────────────────────

@runtime_checkable
class VectorStore(Protocol):
    async def retrieve(
        self,
        query: str,
        restaurant_id: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """쿼리와 restaurant_id 필터로 관련 리뷰를 반환.

        Returns:
            [{"comment": str, "rating": int, "score": float}, ...]
        """
        ...


# ── Pinecone 구현체 ────────────────────────────────────────────────────────

class PineconeStore:
    """Pinecone 기반 리뷰 벡터 스토어."""

    def __init__(self, api_key: str, index_name: str) -> None:
        from pinecone import Pinecone
        pc = Pinecone(api_key=api_key)
        self._index = pc.Index(index_name)
        self._embed_model = "text-embedding-3-small"
        logger.info("[RAG] PineconeStore 초기화: index=%s", index_name)

    def _embed(self, text: str) -> List[float]:
        """텍스트를 임베딩 벡터로 변환 (동기, OpenAI API)."""
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.embeddings.create(input=text, model=self._embed_model)
        return response.data[0].embedding

    async def retrieve(
        self,
        query: str,
        restaurant_id: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        import asyncio
        vector = await asyncio.get_event_loop().run_in_executor(
            None, self._embed, query
        )
        result = self._index.query(
            vector=vector,
            top_k=top_k,
            filter={"restaurant_id": {"$eq": restaurant_id}},
            include_metadata=True,
            namespace="reviews",
        )
        return [
            {
                "comment": m.metadata.get("comment", ""),
                "rating": m.metadata.get("rating", 0),
                "score": round(m.score, 4),
            }
            for m in result.matches
            if m.metadata
        ]


# ── NullStore (RAG 비활성화 시 fallback) ──────────────────────────────────

class NullStore:
    """Pinecone 미설정 시 항상 빈 결과를 반환하는 no-op 구현체."""

    async def retrieve(self, query: str, restaurant_id: str, top_k: int = 5) -> List[Dict]:
        return []


# ── 싱글톤 팩토리 ──────────────────────────────────────────────────────────

_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """모듈 레벨 싱글톤 반환. 설정 없으면 NullStore."""
    global _store
    if _store is not None:
        return _store

    api_key = settings.PINECONE_API_KEY
    index_name = settings.PINECONE_INDEX_NAME

    if not api_key:
        logger.warning("[RAG] PINECONE_API_KEY 미설정 — RAG 비활성화")
        _store = NullStore()
        return _store

    try:
        _store = PineconeStore(api_key=api_key, index_name=index_name)
    except Exception:
        logger.warning("[RAG] PineconeStore 초기화 실패 — RAG 비활성화", exc_info=True)
        _store = NullStore()
    return _store


# ── 포맷 헬퍼 ──────────────────────────────────────────────────────────────

def format_retrieved_reviews(reviews: List[Dict[str, Any]]) -> str:
    """retrieve 결과를 분석가 프롬프트에 삽입할 텍스트로 변환.

    예시 출력:
        ⭐⭐⭐⭐⭐ "단체석 넓고 주차도 편해요. 회식으로 딱 좋습니다."
        ⭐⭐⭐⭐ "가격 대비 양이 많고 고기 질도 좋아요."
    """
    if not reviews:
        return ""
    lines = []
    for r in reviews:
        stars = "⭐" * max(1, min(5, int(r.get("rating", 3))))
        comment = r.get("comment", "").strip()
        if comment:
            lines.append(f'{stars} "{comment}"')
    return "\n".join(lines)
```

---

## Step 4. 인덱싱 스크립트 (`scripts/index_reviews.py`)

프로젝트 루트에서 `python -m services.agent_dialogue.scripts.index_reviews` 로 실행.

```python
"""MongoDB reviews 컬렉션을 Pinecone에 인덱싱하는 1회성 배치 스크립트.

실행:
    python -m services.agent_dialogue.scripts.index_reviews

환경변수:
    PINECONE_API_KEY, PINECONE_INDEX_NAME, MONGODB_URI, OPENAI_API_KEY
"""
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from services.agent_dialogue.app.utils.logging_config import setup_logging
setup_logging()

from shared.database.db_manager import DBManager
from shared.utils.config import settings

logger = logging.getLogger(__name__)

_EMBED_BATCH_SIZE = 100   # OpenAI embeddings API 배치 크기
_UPSERT_BATCH_SIZE = 100  # Pinecone upsert 배치 크기
_EMBED_MODEL = "text-embedding-3-small"
_NAMESPACE = "reviews"


# ── 임베딩 ────────────────────────────────────────────────────────────────

def embed_batch(texts: List[str]) -> List[List[float]]:
    """텍스트 배치를 임베딩 벡터 배열로 변환."""
    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.embeddings.create(input=texts, model=_EMBED_MODEL)
    return [item.embedding for item in response.data]


# ── Pinecone 초기화 ────────────────────────────────────────────────────────

def get_pinecone_index():
    from pinecone import Pinecone
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    return pc.Index(settings.PINECONE_INDEX_NAME)


# ── 메인 인덱싱 로직 ───────────────────────────────────────────────────────

async def fetch_all_reviews() -> List[Dict[str, Any]]:
    """MongoDB reviews 컬렉션 전체 fetch."""
    db = DBManager(col_name="reviews")
    try:
        docs = await db.read_all({})
        logger.info("[인덱싱] 리뷰 fetch 완료: %d건", len(docs))
        return docs
    finally:
        db.client.close()


def build_vectors(
    reviews: List[Dict[str, Any]],
    embeddings: List[List[float]],
) -> List[Dict[str, Any]]:
    """Pinecone upsert 포맷으로 변환."""
    vectors = []
    for review, embedding in zip(reviews, embeddings):
        restaurant_id = str(review.get("restaurantId") or review.get("restaurant_id") or "")
        user_id = str(review.get("userId") or review.get("user_id") or "")
        if not restaurant_id:
            continue
        vectors.append({
            "id": f"{restaurant_id}_{user_id}",
            "values": embedding,
            "metadata": {
                "restaurant_id": restaurant_id,
                "rating": int(review.get("rating", 0)),
                "comment": str(review.get("comment", ""))[:1000],  # 메타데이터 크기 제한
            },
        })
    return vectors


async def run_indexing() -> None:
    if not settings.PINECONE_API_KEY:
        logger.error("PINECONE_API_KEY가 설정되지 않았습니다.")
        return

    index = get_pinecone_index()
    reviews = await fetch_all_reviews()

    if not reviews:
        logger.warning("리뷰 데이터가 없습니다.")
        return

    total = len(reviews)
    success = 0
    failed = 0
    t0 = time.monotonic()

    for i in range(0, total, _EMBED_BATCH_SIZE):
        batch = reviews[i : i + _EMBED_BATCH_SIZE]
        texts = [r.get("comment", "") for r in batch]

        # 빈 코멘트 스킵
        valid_indices = [j for j, t in enumerate(texts) if t.strip()]
        if not valid_indices:
            continue
        valid_batch = [batch[j] for j in valid_indices]
        valid_texts = [texts[j] for j in valid_indices]

        try:
            embeddings = embed_batch(valid_texts)
        except Exception:
            logger.warning("임베딩 실패 (batch %d~%d)", i, i + len(batch), exc_info=True)
            failed += len(valid_batch)
            continue

        vectors = build_vectors(valid_batch, embeddings)

        # Pinecone upsert (배치)
        for j in range(0, len(vectors), _UPSERT_BATCH_SIZE):
            upsert_batch = vectors[j : j + _UPSERT_BATCH_SIZE]
            try:
                index.upsert(vectors=upsert_batch, namespace=_NAMESPACE)
                success += len(upsert_batch)
            except Exception:
                logger.warning("Pinecone upsert 실패", exc_info=True)
                failed += len(upsert_batch)

        logger.info("[인덱싱] 진행: %d / %d (성공=%d, 실패=%d)", i + len(batch), total, success, failed)

    elapsed = time.monotonic() - t0
    logger.info(
        "[인덱싱] 완료: 전체=%d, 성공=%d, 실패=%d, 소요=%.1fs",
        total, success, failed, elapsed,
    )


if __name__ == "__main__":
    asyncio.run(run_indexing())
```

---

## Step 5. `restaurant_dialogue.py` 수정

### 5-1. import 추가

```python
# 기존 import에 추가
from services.agent_dialogue.app.utils.rag import format_retrieved_reviews, get_vector_store
```

### 5-2. 그룹 컨텍스트 포맷 헬퍼 추가

```python
def _build_group_context(
    user_data_list: List[Dict[str, Any]],
    dining_data: Dict[str, Any],
) -> str:
    """RAG 쿼리에 사용할 그룹 컨텍스트 문자열 생성.

    예시: "4명, 예산 30000원, 알러지: 갑각류 땅콩"
    """
    parts = []

    headcount = dining_data.get("headcount")
    if headcount:
        parts.append(f"{headcount}명")

    budget = dining_data.get("budget")
    if budget:
        parts.append(f"예산 {budget:,}원")

    all_allergies = []
    for user in user_data_list:
        all_allergies.extend(user.get("allergies", []))
    unique_allergies = list(dict.fromkeys(all_allergies))  # 순서 유지 dedup
    if unique_allergies:
        parts.append(f"알러지: {' '.join(unique_allergies)}")

    return ", ".join(parts)
```

### 5-3. 분석가 발언 직전 retrieve 호출

`restaurant_dialogue` 노드 내부 `_analyst_speak()` 호출 부분을 아래와 같이 수정:

```python
# 기존
analyst_speech = await _analyst_speak(restaurant_info, dining_info, allergy_info)

# 변경 후
group_context = _build_group_context(user_data_list, dining_data)
retrieved = await _retrieve_reviews_safe(restaurant_id, place_name, group_context)
if retrieved:
    restaurant_info += f"\n\n## 실제 방문 리뷰\n{retrieved}"

analyst_speech = await _analyst_speak(restaurant_info, dining_info, allergy_info)
```

### 5-4. `_retrieve_reviews_safe` 헬퍼 추가

```python
async def _retrieve_reviews_safe(
    restaurant_id: str,
    place_name: str,
    group_context: str,
    top_k: int = 5,
) -> str:
    """RAG 검색 실행. 실패 시 빈 문자열 반환 (분석 흐름 차단하지 않음)."""
    try:
        store = get_vector_store()
        query = f"{place_name} {group_context}".strip()
        reviews = await store.retrieve(query=query, restaurant_id=restaurant_id, top_k=top_k)
        result = format_retrieved_reviews(reviews)
        if result:
            logger.info("[RAG] %s: 리뷰 %d개 retrieve 성공", place_name, len(reviews))
        else:
            logger.info("[RAG] %s: retrieve 결과 없음", place_name)
        return result
    except Exception:
        logger.warning("[RAG] retrieve 실패: %s", place_name, exc_info=True)
        return ""
```

---

## Step 6. Dockerfile.runpod 수정

`requirements.txt`에 `pinecone>=5.0.0` 추가했으므로 Dockerfile은 변경 없음.
(기존 `COPY services/agent_dialogue/requirements.txt` → `pip install` 흐름이 그대로 적용)

---

## Step 7. Pinecone 인덱스 생성 (사전 작업)

Pinecone 대시보드 또는 CLI에서 1회 실행:

```python
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key="...")
pc.create_index(
    name="damo-reviews",
    dimension=1536,        # text-embedding-3-small
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
)
```

---

## 실행 순서 요약

```
1. shared/utils/config.py       PINECONE_API_KEY, PINECONE_INDEX_NAME 필드 추가
2. .env                         PINECONE_API_KEY=... 추가
3. Pinecone 대시보드             인덱스 생성 (dimension=1536, metric=cosine)
4. requirements.txt              pinecone>=5.0.0 추가
5. app/utils/rag.py              VectorStore Protocol + PineconeStore + NullStore
6. scripts/index_reviews.py      인덱싱 스크립트 작성
7. python -m services.agent_dialogue.scripts.index_reviews  인덱싱 실행
8. app/nodes/restaurant_dialogue.py  _build_group_context, _retrieve_reviews_safe 추가 + 통합
9. streamlit_app.py로 로컬 테스트   리뷰 텍스트가 분석가 발언에 반영되는지 확인
10. Langfuse trace에서            retrieve 결과 → 분석가 발언 품질 비교 확인
```

---

## 프로덕션 전환 (Qdrant) 시 변경 범위

`rag.py`에 `QdrantStore` 클래스만 추가하고 `get_vector_store()` 팩토리에서 분기:

```python
# config.py에 추가
VECTOR_STORE: str = "pinecone"  # "pinecone" | "qdrant"
QDRANT_URL: str = ""
QDRANT_COLLECTION: str = "damo-reviews"

# rag.py get_vector_store() 수정
if settings.VECTOR_STORE == "qdrant":
    _store = QdrantStore(url=settings.QDRANT_URL, collection=settings.QDRANT_COLLECTION)
else:
    _store = PineconeStore(...)
```

`restaurant_dialogue.py` 코드는 전혀 변경 없음.

---

## 주의사항

| 항목 | 내용 |
|---|---|
| 임베딩 비용 | text-embedding-3-small 기준 $0.02 / 1M 토큰. 리뷰 10만 건 × 평균 50토큰 = 5M 토큰 ≈ $0.10 |
| 메타데이터 크기 | Pinecone 메타데이터 상한 40KB/벡터. `comment`는 1000자로 truncate |
| 재인덱싱 | 리뷰 추가 시 스크립트 재실행. upsert이므로 중복 없음 |
| RAG 레이턴시 | 임베딩 + Pinecone 쿼리 ≈ 300~500ms 추가. 분석가 발언 1회당 1회만 호출 |
| NullStore | PINECONE_API_KEY 없으면 자동으로 RAG skip. 기존 동작 보존 |
