# agent_dialogue RAG 설계 문서

## 1. 개요

분석가(`restaurant_dialogue`)가 현재 정형 데이터(메뉴, 가격, 편의시설 등)만 보고 발언하는 한계를
실제 리뷰 원문 기반 RAG로 보완하여 분석 품질을 높인다.

---

## 2. 현재 구조의 한계

| 항목 | 현재 | RAG 도입 후 |
|---|---|---|
| 분석 근거 | `review_keywords` (상위 5개 키워드) | 실제 리뷰 원문 top-k개 |
| 리뷰 정보 | 정제된 키워드만 | 구체적 경험담, 감성 표현 |
| 분석 예시 | "분위기 좋음, 가성비" | "단체석 6인 가능, 소고기 육회가 특히 좋다는 후기 다수" |

---

## 3. 데이터 소스

**MongoDB `reviews` 컬렉션** (이미 존재)

```python
class ReviewData(BaseModel):
    restaurant_id: str   # 식당 ID (필터 키)
    user_id: int
    rating: int          # 평점 (메타데이터로 활용)
    comment: str         # 임베딩 대상 원문
```

---

## 4. 시스템 구성

### 4-1. 인프라

| 컴포넌트 | 선택 | 비고 |
|---|---|---|
| 벡터 DB | **Pinecone** (테스트) → **Qdrant** (프로덕션) | Railway MongoDB가 Atlas 미지원 |
| 임베딩 모델 | **text-embedding-3-small** (테스트) → **BGE-M3** (프로덕션) | 테스트는 OpenAI API, 프로덕션은 vLLM 로컬 서빙 |

### 4-2. 전체 파이프라인

```
[오프라인 인덱싱 — 1회성 배치]

MongoDB reviews
  └─ comment + restaurant_id + rating 추출
  └─ text-embedding-3-small 임베딩
  └─ Pinecone upsert
       메타데이터: { restaurant_id, rating }
       벡터 ID: "{restaurant_id}_{user_id}"

[온라인 검색 — restaurant_dialogue 실행 시]

현재 식당 + 그룹 컨텍스트
  └─ 쿼리 생성: "{place_name} {알러지} {예산} {인원}"
  └─ Pinecone query
       filter: { restaurant_id: { "$eq": current_restaurant_id } }
       top_k: 5
  └─ retrieved 리뷰 → restaurant_info에 추가
  └─ _analyst_speak() 호출
```

---

## 5. 코드 통합 위치

**`services/agent_dialogue/app/nodes/restaurant_dialogue.py`**

`_analyst_speak()` 호출 직전에 `_retrieve_reviews()` 헬퍼 추가:

```python
async def _retrieve_reviews(
    restaurant_id: str,
    place_name: str,
    group_context: str,   # "4명, 예산 3만원, 갑각류 알러지"
    top_k: int = 5,
) -> str:
    """벡터 DB에서 관련 리뷰 retrieve.

    실패 시 빈 문자열 반환 (분석가 발언은 계속 진행).
    """
    ...
```

```python
# restaurant_dialogue 노드 내부
retrieved_reviews = await _retrieve_reviews(
    restaurant_id=restaurant_id,
    place_name=place_name,
    group_context=_build_group_context(user_data_list, dining_data),
)

# restaurant_info에 리뷰 섹션 추가
if retrieved_reviews:
    restaurant_info += f"\n\n## 관련 리뷰\n{retrieved_reviews}"

analyst_speech = await _analyst_speak(restaurant_info, dining_info, allergy_info)
```

---

## 6. 인덱싱 스크립트 구성

**`services/agent_dialogue/scripts/index_reviews.py`**

```
1. MongoDB reviews 컬렉션 전체 fetch
2. comment 텍스트 임베딩 (배치 처리, rate limit 고려)
3. Pinecone upsert
   - namespace: "reviews"
   - 벡터 ID: "{restaurant_id}_{user_id}"
   - 메타데이터: { restaurant_id, rating }
4. 완료 후 통계 출력 (총 문서 수, 실패 건수)
```

---

## 7. 쿼리 전략

| 항목 | 내용 |
|---|---|
| 쿼리 텍스트 | `"{place_name} {dining_context}"` |
| 필터 | `restaurant_id == 현재 식당` (다른 식당 리뷰 오염 방지) |
| top_k | 5개 (컨텍스트 길이 vs 품질 균형) |
| 실패 처리 | 예외 시 빈 문자열 반환 → 분석은 정형 데이터만으로 계속 |
| 평점 가중 | rating 높은 리뷰 우선 (메타데이터 필터 또는 후처리) |

---

## 8. 환경변수 추가

```
# 벡터 DB
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=damo-reviews

# 임베딩 (테스트: OpenAI 재사용, 프로덕션: 별도 엔드포인트)
EMBEDDING_MODEL=text-embedding-3-small
```

---

## 9. 구현 순서

```
Step 1  Pinecone 인덱스 생성 (dimension=1536, metric=cosine)
Step 2  scripts/index_reviews.py — MongoDB → Pinecone 인덱싱
Step 3  utils/rag.py — retrieve 함수 구현
Step 4  restaurant_dialogue.py — _retrieve_reviews() 통합
Step 5  config.py — PINECONE_API_KEY 등 환경변수 추가
Step 6  Dockerfile.runpod — pinecone-client 의존성 추가
Step 7  테스트 및 리뷰 품질 확인 (Langfuse trace에서 retrieved 리뷰 확인)
```

---

## 10. 프로덕션 전환 계획

| 항목 | 테스트 | 프로덕션 |
|---|---|---|
| 벡터 DB | Pinecone (무료 티어) | Qdrant (Docker, RunPod 동일 인스턴스) |
| 임베딩 | text-embedding-3-small (OpenAI API) | BGE-M3 (vLLM으로 로컬 서빙) |
| 인덱싱 비용 | ~$0.02 / 1M 토큰 | 무료 |
| 검색 비용 | Pinecone 무료 티어 한도 내 | 무료 |

Qdrant 전환 시 `utils/rag.py`의 클라이언트 구현체만 교체하면 되도록
인터페이스를 추상화하여 작성한다.
