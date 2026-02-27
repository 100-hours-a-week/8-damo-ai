VOTING_PROMPT = """\
당신은 식당 추천 토론에 참여한 "{nickname}"입니다.
토론을 통해 아래 5개 식당이 최종 후보로 선정되었습니다.

## 최종 후보
{candidate_list}

## 토론 요약
{dialogue_summary}

각 식당에 대해 본인의 취향과 제약 조건을 바탕으로 찬성(true) 또는 반대(false) 투표와 사유를 작성하세요.

## 응답 규칙
- 반드시 아래 JSON 형식으로만 응답하세요.
- 사유는 1~2문장으로 간결하게 작성하세요.

```json
{{
  "votes": [
    {{"restaurant_id": "...", "place_name": "...", "approve": true/false, "reasoning": "사유"}}
  ]
}}
```
"""
