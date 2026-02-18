CONSENSUS_ASSESSMENT_PROMPT = """\
당신은 식당 추천 토론의 중립적인 판정자입니다.

아래 토론 내용을 분석하여, 참여자들이 공통으로 긍정적으로 언급한 식당 5개를 추출하세요.

## 후보 식당 목록
{candidate_list}

## 토론 내용
{dialogue_history}

## 응답 규칙
- 반드시 아래 JSON 형식으로만 응답하세요.
- 5개 이상 합의된 식당이 있으면 `consensus_reached`를 true로 설정하세요.
- 5개 미만이면 `consensus_reached`를 false로 설정하세요.

```json
{{
  "consensus_reached": true/false,
  "candidates": [
    {{"restaurant_id": "...", "place_name": "...", "reason": "합의 사유"}}
  ]
}}
```
"""

DEADLOCK_RESOLUTION_PROMPT = """\
당신은 식당 추천 토론의 중립적인 판정자입니다.
최대 라운드에 도달했으나 합의가 이루어지지 않았습니다.

아래 토론 내용에서 긍정적으로 가장 많이 언급된 식당 5개를 강제 선정하세요.

## 후보 식당 목록
{candidate_list}

## 전체 토론 내용
{dialogue_history}

## 응답 규칙
- 반드시 아래 JSON 형식으로만 응답하세요.
- 긍정 언급 빈도가 높은 순으로 5개를 선정하세요.

```json
{{
  "consensus_reached": true,
  "candidates": [
    {{"restaurant_id": "...", "place_name": "...", "reason": "선정 사유"}}
  ]
}}
```
"""
