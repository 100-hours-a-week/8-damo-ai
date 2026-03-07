# v1.5 — Lost in the Middle 개선: previous_messages 앞으로, candidate_list 뒤로 이동
# v1.4 — 응답 길이 80자로 완화, 나열·요약 패턴 명시적 금지
# v1.3 — 회식 정보(예산, 날짜) 추가
# v1.2 — 라운드 2+ 프롬프트 차별화: 이전 대화 기반 논의 발전 유도
# v1.1 — 대화 자유도 개선: 반응 강제 제거, 자연스러운 흐름 유도
# v1.0 — 메뉴 데이터 참고 추가, 30자 제한 적용
DIALOGUE_PROMPT_VERSION = "v1.5"

DIALOGUE_USER_PROMPT = """\
이전 대화:
{previous_messages}

이전 대화에서 나온 의견들을 바탕으로, 논의를 발전시켜 주세요.

회식 정보:
{dining_info}

현재 후보 식당 목록:
{candidate_list}

규칙:
- 이전 라운드에서 했던 말을 반복하지 마세요.
- 아직 언급되지 않은 식당에 대해 새로운 의견을 꺼내거나, 기존 의견에 대해 찬반을 표현하세요.
- 싫은 식당이 있으면 왜 싫은지도 솔직하게 말하세요 (알레르기, 취향 등).
- 반드시 80자 이내로 작성하세요.
- 지금 하고 싶은 말 하나만 짧게 하세요. 여러 식당을 나열하거나 "최종 의견"처럼 정리하지 마세요.
"""

FIRST_ROUND_USER_PROMPT = """\
회식 정보:
{dining_info}

현재 후보 식당 목록:
{candidate_list}

당신이 첫 번째로 말합니다. 위 후보를 보고 가고 싶은 식당 1~2곳을 골라주세요.

규칙:
- 왜 그 식당에 가고 싶은지 구체적으로 말하세요 (메뉴가 맛있을 것 같다, 가격이 괜찮다, 분위기가 좋을 것 같다 등).
- 가기 싫은 식당이 있으면 이유와 함께 말해도 됩니다.
- 반드시 80자 이내로 작성하세요.
- 지금 하고 싶은 말 하나만 짧게 하세요. 여러 식당을 나열하거나 "최종 의견"처럼 정리하지 마세요.
"""

GUIDED_ROUND_USER_PROMPT = """\
이전 대화:
{previous_messages}

사회자 안내:
{moderator_feedback}

위 사회자의 정리를 참고하여 대화에 참여하세요.

회식 정보:
{dining_info}

현재 후보 식당 목록:
{candidate_list}

규칙:
- 사회자가 언급한 식당에 대해 의견을 말하되, 다른 식당 얘기도 자유롭게 해도 됩니다.
- 다른 사람 의견에 공감하거나 반박해도 되고, 새로운 의견을 꺼내도 됩니다.
- 반드시 80자 이내로 작성하세요.
- 지금 하고 싶은 말 하나만 짧게 하세요. 여러 식당을 나열하거나 "최종 의견"처럼 정리하지 마세요.
"""

# Chat 타입 프롬프트용 fallback (Langfuse chat 타입 연결 실패 시 사용)
# placeholder: 현재 페르소나 발언 = assistant, 나머지 = user 로 변환된 메시지 리스트 주입
DIALOGUE_CHAT_FALLBACK = [
    {"role": "placeholder", "variable_name": "previous_messages"},
    {
        "role": "user",
        "content": (
            "이전 대화에서 나온 의견들을 바탕으로, 논의를 발전시켜 주세요.\n\n"
            "회식 정보:\n{dining_info}\n\n"
            "현재 후보 식당 목록:\n{candidate_list}\n\n"
            "규칙:\n"
            "- 이전 라운드에서 했던 말을 반복하지 마세요.\n"
            "- 아직 언급되지 않은 식당에 대해 새로운 의견을 꺼내거나, 기존 의견에 대해 찬반을 표현하세요.\n"
            "- 싫은 식당이 있으면 왜 싫은지도 솔직하게 말하세요 (알레르기, 취향 등).\n"
            "- 반드시 80자 이내로 작성하세요.\n"
            '- 지금 하고 싶은 말 하나만 짧게 하세요. 여러 식당을 나열하거나 "최종 의견"처럼 정리하지 마세요.'
        ),
    },
]

FIRST_ROUND_CHAT_FALLBACK = [{"role": "user", "content": FIRST_ROUND_USER_PROMPT}]

RESTAURANT_SUMMARIZER_CHAT_FALLBACK = [
    {
        "role": "system",
        "content": "당신은 식당 정보를 한국어로 간결하게 요약하는 도우미입니다.",
    },
    {
        "role": "user",
        "content": (
            "다음 식당 정보를 2~3문장으로 요약해주세요.\n"
            "메뉴와 특징을 중심으로, 회식 선택에 도움이 될 내용을 담아주세요.\n\n"
            "식당명: {place_name} ({category_detail})\n"
            "메뉴: {menus}\n"
            "편의시설: {amenities}\n"
            "리뷰 키워드: {keywords}\n\n"
            "요약:"
        ),
    },
]

GUIDED_ROUND_CHAT_FALLBACK = [
    {"role": "placeholder", "variable_name": "previous_messages"},
    {
        "role": "user",
        "content": (
            "사회자 안내:\n{moderator_feedback}\n\n"
            "위 사회자의 정리를 참고하여 대화에 참여하세요.\n\n"
            "회식 정보:\n{dining_info}\n\n"
            "현재 후보 식당 목록:\n{candidate_list}\n\n"
            "규칙:\n"
            "- 사회자가 언급한 식당에 대해 의견을 말하되, 다른 식당 얘기도 자유롭게 해도 됩니다.\n"
            "- 다른 사람 의견에 공감하거나 반박해도 되고, 새로운 의견을 꺼내도 됩니다.\n"
            "- 반드시 80자 이내로 작성하세요.\n"
            '- 지금 하고 싶은 말 하나만 짧게 하세요. 여러 식당을 나열하거나 "최종 의견"처럼 정리하지 마세요.'
        ),
    },
]
