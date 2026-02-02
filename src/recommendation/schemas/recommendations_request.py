from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import List, Optional
from src.recommendation.schemas.dining_data import DiningData
from src.recommendation.schemas.restaurant_vote_result import RestaurantVoteResult


class RecommendationsRequest(BaseModel):
    """
    추천을 위한 사용자 데이터 요청 모델입니다.
    회식 데이터와 사용자 데이터를 함께 전달받아 처리합니다.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "diningData": {
                    "diningId": 12345,
                    "groupsId": 678,
                    "diningDate": "2025-01-29T15:00:00",
                    "budget": 100000,
                    "x": "127.1111",
                    "y": "37.3947"
                },
                "userIds": [9980731, 2779115, 2667650],
                "voteResultList": [
                    {
                        "restaurantId": "objectId",
                        "likeCount": 1,
                        "dislikeCount": 2,
                        "likedUserIds": [2779115],
                        "dislikedUserIds": [9980731, 2667650]
                    }
                ]
            }
        }
    )

    dining_data: DiningData = Field(..., description="회식 데이터")
    user_ids: List[int] = Field(..., description="추천할 사용자 id 리스트")
     # Optional로 추가 (재추천 시에만 전달됨)
    vote_result_list: Optional[List[RestaurantVoteResult]] = Field(
        None, description="식당 투표 결과 리스트 (재추천/새로고침 시 필수)"
    )
