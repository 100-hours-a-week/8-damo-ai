from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Persona(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int = Field(..., description="사용자 ID")
    nickname: str = Field(..., description="닉네임")
    persona: str = Field(..., alias="basePersona", description="페르소나")
