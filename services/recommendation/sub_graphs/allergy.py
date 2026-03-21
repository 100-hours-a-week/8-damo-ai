"""알러지 서브그래프.

기존 recommend.py의 allergy_node를 독립 파일로 분리하고
소프트 패널티 방식(allergy_penalty + allergy_hints)으로 동작한다.

recommend.py의 기존 allergy_node/ALLERGY_KEYWORDS는 수정하지 않음.
"""

import logging

from langgraph.graph import StateGraph, START, END

from services.recommendation.state import RecommendationState
from shared.database.db_manager import DBManager

logger = logging.getLogger(__name__)

# ─── 알러지 키워드 매핑 (recommend.py와 동일, 독립 유지) ──────────────────────

ALLERGY_KEYWORDS: dict[str, list[str]] = {
    "LEGUMES": ["콩", "대두", "완두", "강낭콩"],
    "NUTS": ["땅콩", "호두", "잣", "캐슈넛", "아몬드"],
    "SHELLFISH": ["조개", "굴", "전복", "소라", "해방풍"],
    "FISH": ["생선", "고등어", "연어", "조기", "갈치"],
    "GRAINS": ["밀", "보리", "곡물", "호밀"],
    "MILK": ["우유", "치즈", "버터", "크림", "유제품"],
    "SHRIMP": ["새우", "대하", "중하"],
    "OYSTER": ["굴", "석화"],
    "CRAB": ["게", "대게", "킹크랩"],
    "MUSSEL": ["홍합"],
    "SQUID": ["오징어", "낙지", "문어"],
    "ABALONE": ["전복"],
    "MACKEREL": ["고등어"],
    "BUCKWHEAT": ["메밀", "소바"],
    "WHEAT": ["밀가루", "소맥"],
    "SOYBEAN": ["대두", "콩"],
    "WALNUT": ["호두"],
    "PEANUT": ["땅콩"],
    "PINE_NUT": ["잣"],
    "EGG": ["계란", "달걀", "난류"],
    "BEEF": ["소고기", "쇠고기", "육회"],
    "PORK": ["돼지고기", "돼지", "제육", "삼겹살"],
    "CHICKEN": ["닭고기", "치킨"],
    "PEACH": ["복숭아"],
    "TOMATO": ["토마토"],
    "SULFITES": ["아황산", "방부제"],
}

_RISK_THRESHOLD = 0.5   # 이 이상이면 risky_user로 판정
_PENALTY_CAP = 0.3      # 패널티 최댓값


# ─── 내부 유틸 ────────────────────────────────────────────────────────────────

def _calculate_dynamic_score(menus: list[dict], allergy: str) -> float:
    """메뉴명 키워드 매칭 기반 실시간 위험도 (0.0 ~ 1.0).

    상위 3개 메뉴는 가중치 2배 적용.
    menus의 title 또는 name 필드를 참조한다.
    """
    if not menus:
        return 0.0

    keywords = ALLERGY_KEYWORDS.get(allergy, [allergy.lower()])
    total_weight = 0.0
    matched_weight = 0.0

    for idx, menu in enumerate(menus):
        name = (menu.get("title") or menu.get("name") or "").lower()
        weight = 2.0 if idx < 3 else 1.0
        total_weight += weight
        if any(kw in name for kw in keywords):
            matched_weight += weight

    if total_weight == 0.0:
        return 0.0
    return round(matched_weight / total_weight, 4)


# ─── 패널티 & 하드제외 계산 ───────────────────────────────────────────────────

def _calculate_allergy_penalty(
    user_datas: list[dict],
    restaurant: dict,
) -> tuple[float, list[str]]:
    """소프트 패널티와 LLM 힌트를 반환한다.

    Returns:
        allergy_penalty: 0.0 ~ 0.3 (cap 적용)
        allergy_hints:   ["유저1 - PORK 메뉴 주의", ...]
    """
    total_users = len(user_datas)
    if total_users == 0:
        return 0.0, []

    kag_risk_map = restaurant.get("allergy_risk_map", {})
    menus = restaurant.get("menus", [])

    risky_users = 0
    total_risk = 0.0
    hints: list[str] = []

    for user in user_datas:
        max_risk = 0.0
        for allergy in user.get("allergies", []):
            kag = kag_risk_map.get(allergy, 0.0)
            dynamic = _calculate_dynamic_score(menus, allergy)
            score = max(kag, dynamic)
            max_risk = max(max_risk, score)
            if score >= _RISK_THRESHOLD:
                hints.append(f"유저{user['id']} - {allergy} 메뉴 주의")
        if max_risk >= _RISK_THRESHOLD:
            risky_users += 1
            total_risk += max_risk

    if risky_users == 0:
        return 0.0, hints

    avg_risk = total_risk / risky_users
    penalty = (risky_users / total_users) * avg_risk
    return min(round(penalty, 4), _PENALTY_CAP), hints


def _is_hard_exclude(user_datas: list[dict], restaurant: dict) -> bool:
    """하드 제외 조건 판정.

    조건: 상위 3개 메뉴 중 80% 이상이 특정 알러지 키워드에 매칭 AND
          전체 유저의 50% 이상이 해당 알러지 보유.
    """
    top_menus = restaurant.get("menus", [])[:3]
    if not top_menus:
        return False

    total = len(user_datas)
    if total == 0:
        return False

    risky = 0
    for user in user_datas:
        for allergy in user.get("allergies", []):
            keywords = ALLERGY_KEYWORDS.get(allergy, [])
            matched = sum(
                1
                for m in top_menus
                if any(kw in (m.get("title") or m.get("name") or "").lower() for kw in keywords)
            )
            if matched / len(top_menus) >= 0.8:
                risky += 1
                break  # 한 알러지로 이미 위험 판정 → 다음 유저로

    return risky / total >= 0.5


# ─── 알러지 노드 ──────────────────────────────────────────────────────────────

async def allergy_node(state: RecommendationState) -> dict:
    """알러지 소프트 패널티 계산 노드.

    - 유저 DB 조회 → 알러지 목록 수집
    - 식당별 allergy_penalty, allergy_hints 계산
    - 하드 제외 조건 충족 식당은 제거
    - filtered_restaurant에 결과를 포함하여 반환 (state 포함 필수)
    """
    user_ids = state.get("user_ids", [])
    logger.info("[ALLERGY] 시작: user_ids=%s", user_ids)

    db = DBManager()
    db.set_collection("users")

    user_datas: list[dict] = []
    for uid in user_ids:
        user = await db.read_one({"id": {"$in": [str(uid), int(uid)]}})
        if user is None:
            logger.warning("[ALLERGY] 유저 없음 → 구제 경로: user_id=%s", uid)
            return {
                "is_error": True,
                "error_message": f"User not found in DB: {uid}",
                "status_message": f"유저(ID: {uid}) 정보를 찾을 수 없어 알러지 필터링을 건너뜁니다.",
                # filtered_restaurant 유지 — rescue_from_error가 점수 기반 추천에 사용
            }
        user_datas.append(user)

    filtered = state.get("filtered_restaurant", [])
    result: list[dict] = []

    for restaurant in filtered:
        # 하드 제외 먼저 검사
        if _is_hard_exclude(user_datas, restaurant):
            logger.info(
                "[ALLERGY] 하드 제외: %s", restaurant.get("place_name", "unknown")
            )
            continue

        penalty, hints = _calculate_allergy_penalty(user_datas, restaurant)
        restaurant["allergy_penalty"] = penalty
        restaurant["allergy_hints"] = hints
        result.append(restaurant)

    logger.info("[ALLERGY] 완료: %d/%d 식당 생존", len(result), len(filtered))

    return {
        "filtered_restaurant": result,
        "status_message": f"알러지 필터링 완료: {len(result)}개 생존",
    }


# ─── 서브그래프 팩토리 ────────────────────────────────────────────────────────

def get_allergy_graph():
    """allergy_sg 서브그래프를 빌드하여 반환한다."""
    workflow = StateGraph(RecommendationState)
    workflow.add_node("allergy", allergy_node)
    workflow.add_edge(START, "allergy")
    workflow.add_edge("allergy", END)
    return workflow.compile()
