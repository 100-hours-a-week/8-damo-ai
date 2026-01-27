from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class RecommendedItem(BaseModel):
    """추천 식당 아이템"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    restaurant_id: str = Field(..., description="식당 식별자")
    reasoning_description: str = Field(..., max_length=500, description="추천 사유")
