from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import List
from src.recommendation.schemas.user_data import UserData
from src.recommendation.schemas.review_data import ReviewData


class UpdatePersonaDBRequest(BaseModel):
    """
    페르소나 업데이트를 위한 사용자 데이터 요청
        1. UserData: 사용자 정보
        2. ReviewData: 해당 사용자가 작성한 리뷰 데이터
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    user_data: UserData = Field(..., description="업데이트할 사용자 데이터")
    review_data: List[ReviewData] = Field(..., description="리뷰 데이터 리스트")
