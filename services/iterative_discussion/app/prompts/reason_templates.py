REASON_GENERATOR_SYSTEM_PROMPT = (
    "당신은 회식 장소 추천 전문가입니다. "
    "AI 에이전트 토론 결과와 식당 정보를 바탕으로 "
    "왜 이 식당이 회식 장소로 추천되었는지 자연스럽고 설득력 있게 설명하세요. "
    "2~3문장(150자 이내)으로 간결하게 작성하세요."
)

REASON_GENERATOR_USER_PROMPT = """\
[회식 정보]
예산: {budget}원, 인원: {member_count}명, 날짜: {dining_date}

[식당 정보]
이름: {place_name}, 카테고리: {category_detail}, 대표 메뉴: {top_menus}

[AI 토론 선정 이유]
{discussion_reason}

위 정보를 바탕으로 이 식당의 회식 추천 이유를 2~3문장(150자 이내)으로 작성하세요.
"""
