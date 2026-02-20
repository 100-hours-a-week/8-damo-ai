CONSENSUS_ASSESSMENT_PROMPT = """\
당신은 식당 추천 토론의 중립적인 판정자입니다.

아래 토론 내용을 분석하여:
1. 참여자들이 **긍정적으로** 언급한 식당을 추출하세요.
2. 참여자들이 **부정적으로** 언급한 식당(알레르기, 취향 거부, 반대 의견)도 추출하세요.

## 후보 식당 목록
{candidate_list}

## 토론 내용
{dialogue_history}

## 응답 규칙
- 반드시 아래 JSON 형식으로만 응답하세요.
- 참여자 과반수가 긍정적으로 언급한 식당이 5개 이상일 때만 `consensus_reached`를 true로 설정하세요.
- 5개 미만이면 반드시 `consensus_reached`를 false로 설정하세요.
- `candidates`: 과반수 긍정을 받은 식당만 포함 (빈 리스트도 가능).
- `rejected`: 1명이라도 부정적으로 언급한 식당 전부 (알레르기, 싫다, 별로, 안 맞다 등).

```json
{{
  "consensus_reached": true/false,
  "candidates": [
    {{"restaurant_id": "...", "place_name": "...", "reason": "합의 사유"}}
  ],
  "rejected": [
    {{"restaurant_id": "...", "place_name": "...", "reason": "거부 사유"}}
  ]
}}
```
"""

DEADLOCK_RESOLUTION_PROMPT = """\
당신은 식당 추천 토론의 중립적인 판정자입니다.
최대 라운드에 도달했으나 합의가 이루어지지 않았습니다.

아래 토론 내용을 분석하여:
1. 긍정적으로 가장 많이 언급된 식당 5개를 강제 선정하세요.
2. 부정적으로 언급된 식당도 반드시 추출하세요.

## 후보 식당 목록
{candidate_list}

## 전체 토론 내용
{dialogue_history}

## 응답 규칙
- 반드시 아래 JSON 형식으로만 응답하세요.
- `candidates`: 긍정 언급 빈도가 높은 순으로 5개 선정. 부정 의견이 많은 식당은 제외.
- `rejected`: 1명이라도 부정적으로 언급한 식당 전부.

```json
{{
  "consensus_reached": true,
  "candidates": [
    {{"restaurant_id": "...", "place_name": "...", "reason": "선정 사유"}}
  ],
  "rejected": [
    {{"restaurant_id": "...", "place_name": "...", "reason": "거부 사유"}}
  ]
}}
```
"""
