"""MongoDB → Neo4j 인덱싱 스크립트.

MongoDB restaurants 컬렉션에서 식당 정보를 읽어 GPT-4o-mini로 알러지를 분석하고
결과를 MongoDB와 Neo4j 양쪽에 동시 저장한다. 1회 실행 스크립트.

Usage:
    python scripts/indexing/mongodb_to_neo4j.py [--batch-size N] [--dry-run]

Options:
    --batch-size    LLM 분석 배치 크기 (default: 50)
    --dry-run       Neo4j/MongoDB 저장 없이 분석만 실행
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

# 프로젝트 루트를 sys.path에 추가 (직접 실행 시 shared 모듈 인식)
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── 22종 알러지 타입 ──────────────────────────────────────────────────────────

ALLERGY_TYPES: list[str] = [
    "LEGUMES", "NUTS", "SHELLFISH", "FISH", "GRAINS", "MILK",
    "SHRIMP", "OYSTER", "CRAB", "MUSSEL", "SQUID", "ABALONE",
    "MACKEREL", "BUCKWHEAT", "WHEAT", "SOYBEAN", "WALNUT", "PEANUT",
    "PINE_NUT", "EGG", "BEEF", "PORK", "CHICKEN", "PEACH", "TOMATO", "SULFITES",
]

SCORE_THRESHOLD = 0.3  # 이 미만은 저장하지 않음


# ─── 프롬프트 생성 ────────────────────────────────────────────────────────────

def chunk_allergy_analysis_prompt(restaurant: dict[str, Any]) -> str:
    """식당 메뉴 정보로 LLM 알러지 분석 프롬프트를 생성한다."""
    place_name = restaurant.get("place_name", "미상")
    menus = restaurant.get("menus", [])

    menu_lines: list[str] = []
    for m in menus:
        title = m.get("title") or m.get("name") or ""
        price = m.get("price")
        if title:
            line = f"- {title}" + (f" ({price}원)" if price else "")
            menu_lines.append(line)

    menu_text = "\n".join(menu_lines) if menu_lines else "메뉴 정보 없음"
    allergy_list = ", ".join(ALLERGY_TYPES)

    return (
        f"다음 식당의 메뉴를 보고 한국 식품 알레르기에 대한 위험도를 분석해주세요.\n"
        f"메뉴명과 설명을 참고하여 각 알레르기 항목의 위험도를 0.0~1.0 사이로 답하세요.\n"
        f"위험도 {SCORE_THRESHOLD} 미만인 항목은 생략해도 됩니다.\n\n"
        f"식당명: {place_name}\n"
        f"메뉴 목록:\n{menu_text}\n\n"
        f"반드시 아래 JSON 형식으로만 응답하세요:\n"
        f'{{\"PORK\": 0.9, \"SOYBEAN\": 0.6, ...}}\n\n'
        f"알레르기 종류: {allergy_list}"
    )


# ─── LLM 응답 파싱 ────────────────────────────────────────────────────────────

def parse_llm_response(raw: str) -> dict[str, float]:
    """LLM 응답 문자열에서 알러지 점수 dict를 추출한다.

    - 마크다운 코드블록 제거
    - JSON 파싱 실패 시 빈 dict 반환
    - 점수 0~1 범위 클램핑
    - SCORE_THRESHOLD 미만 제거
    - 알려지지 않은 알러지 타입 제거
    """
    # 마크다운 코드블록 제거 (```json ... ``` 또는 ``` ... ```)
    cleaned = re.sub(r"```(?:json)?\s*([\s\S]*?)\s*```", r"\1", raw.strip())

    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        logger.warning("LLM 응답 JSON 파싱 실패: %s", raw[:100])
        return {}

    if not isinstance(data, dict):
        return {}

    result: dict[str, float] = {}
    for key, value in data.items():
        if key not in ALLERGY_TYPES:
            continue
        try:
            score = float(value)
        except (TypeError, ValueError):
            continue
        score = max(0.0, min(1.0, score))  # 클램핑
        if score >= SCORE_THRESHOLD:
            result[key] = round(score, 4)

    return result


# ─── Neo4j 작업 ───────────────────────────────────────────────────────────────

async def create_allergy_type_nodes(session: Any) -> None:
    """22개 AllergyType 노드를 사전 생성 (MERGE → 중복 없음)."""
    await session.run(
        """
        UNWIND $allergy_names AS name
        MERGE (:AllergyType {name: name})
        """,
        allergy_names=ALLERGY_TYPES,
    )
    logger.info("AllergyType 노드 %d개 MERGE 완료", len(ALLERGY_TYPES))


async def upsert_to_neo4j(
    session: Any,
    restaurant: dict[str, Any],
    allergy_scores: dict[str, float],
) -> None:
    """Restaurant 노드와 HAS_ALLERGY_RISK 관계를 Neo4j에 upsert한다."""
    restaurant_id = str(restaurant.get("_id", ""))
    place_name = restaurant.get("place_name", "")
    category_detail = restaurant.get("category_detail", "")

    # 1. Restaurant 노드 MERGE
    await session.run(
        """
        MERGE (r:Restaurant {id: $restaurant_id})
          ON CREATE SET r.place_name = $place_name,
                        r.category_detail = $category_detail
          ON MATCH  SET r.place_name = $place_name,
                        r.category_detail = $category_detail
        """,
        restaurant_id=restaurant_id,
        place_name=place_name,
        category_detail=category_detail,
    )

    if not allergy_scores:
        return

    # 2. HAS_ALLERGY_RISK 관계 MERGE
    scores_list = [{"name": k, "score": v} for k, v in allergy_scores.items()]
    await session.run(
        """
        MATCH (r:Restaurant {id: $restaurant_id})
        UNWIND $allergy_scores AS item
        MATCH (a:AllergyType {name: item.name})
        MERGE (r)-[rel:HAS_ALLERGY_RISK]->(a)
          ON CREATE SET rel.score = item.score, rel.source = 'llm_analysis'
          ON MATCH  SET rel.score = item.score
        """,
        restaurant_id=restaurant_id,
        allergy_scores=scores_list,
    )


# ─── MongoDB write-back ───────────────────────────────────────────────────────

async def write_back_to_mongo(
    collection: Any,
    restaurant_id: str,
    allergy_risk_map: dict[str, float],
) -> None:
    """allergy_risk_map을 MongoDB restaurants 컬렉션에 $set으로 저장한다."""
    await collection.update_one(
        {"_id": restaurant_id},
        {"$set": {"allergy_risk_map": allergy_risk_map}},
    )


# ─── LLM 호출 ─────────────────────────────────────────────────────────────────

async def analyze_allergy_with_llm(
    client: Any, prompt: str
) -> dict[str, float]:
    """GPT-4o-mini로 알러지 분석 요청 후 파싱된 결과를 반환한다."""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 식품 알레르기 전문가입니다. 요청한 JSON 형식으로만 응답합니다.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=512,
        )
        raw = response.choices[0].message.content or ""
        return parse_llm_response(raw)
    except Exception as e:
        logger.error("LLM 분석 실패: %s", e)
        return {}


# ─── 메인 파이프라인 ──────────────────────────────────────────────────────────

async def run_indexing(batch_size: int = 50, dry_run: bool = False) -> None:
    """MongoDB → 알러지 분석 → Neo4j + MongoDB write-back 전체 파이프라인."""
    # 런타임 임포트 (테스트 시 모킹 가능하도록)
    from openai import AsyncOpenAI
    from motor.motor_asyncio import AsyncIOMotorClient
    from shared.database.neo4j_client import Neo4jClient
    from shared.utils.config import get_settings

    settings = get_settings()

    # 클라이언트 초기화
    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    mongo_client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = mongo_client[settings.DB_NAME]
    collection = db["restaurants"]

    # 식당 목록 조회
    restaurants = await collection.find({}).to_list(length=None)
    logger.info("MongoDB 식당 조회: %d개", len(restaurants))

    if not restaurants:
        logger.warning("처리할 식당이 없습니다.")
        return

    neo4j_driver = await Neo4jClient.get_driver()
    async with neo4j_driver.session() as session:
        # AllergyType 노드 사전 생성
        if not dry_run:
            await create_allergy_type_nodes(session)

        # 배치 처리
        total = len(restaurants)
        for i in range(0, total, batch_size):
            batch = restaurants[i : i + batch_size]
            logger.info("배치 처리 중: %d/%d", min(i + batch_size, total), total)

            for restaurant in batch:
                restaurant_id = str(restaurant.get("_id", ""))
                prompt = chunk_allergy_analysis_prompt(restaurant)
                allergy_scores = await analyze_allergy_with_llm(openai_client, prompt)

                allergy_detail = ", ".join(
                    f"{k}({v:.1f})" for k, v in sorted(allergy_scores.items(), key=lambda x: -x[1])
                ) or "없음"
                logger.info(
                    "[%s] 알러지 %d종 → %s",
                    restaurant.get("place_name", restaurant_id),
                    len(allergy_scores),
                    allergy_detail,
                )

                if dry_run:
                    continue

                # Neo4j upsert
                await upsert_to_neo4j(session, restaurant, allergy_scores)

                # MongoDB write-back
                await write_back_to_mongo(collection, restaurant_id, allergy_scores)

    mongo_client.close()
    await Neo4jClient.close()
    logger.info("인덱싱 완료.")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MongoDB → Neo4j 알러지 인덱싱")
    parser.add_argument("--batch-size", type=int, default=50, help="배치 크기")
    parser.add_argument("--dry-run", action="store_true", help="저장 없이 분석만 실행")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run_indexing(batch_size=args.batch_size, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
