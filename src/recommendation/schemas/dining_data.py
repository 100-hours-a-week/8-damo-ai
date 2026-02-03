from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import List, Optional, Union
from datetime import datetime


class DiningData(BaseModel):
    """회식 데이터 모델"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    dining_id: Union[int, str] = Field(
        ...,
        description="회식 테이블의 PK (snowflake)",
        json_schema_extra={"example": "276899722003304450"},
    )
    groups_id: Union[int, str] = Field(..., description="그룹 테이블의 PK")
    dining_date: datetime = Field(..., description="회식 진행 날짜")
    budget: int = Field(..., description="회식 진행 예산")
    x: str = Field(..., description="경도 (longitude)")
    y: str = Field(..., description="위도 (latitude)")
