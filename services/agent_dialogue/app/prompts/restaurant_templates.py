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
