from pydantic_settings import BaseSettings, SettingsConfigDict
from uuid import uuid4
from shared.schemas.stream_schema import TopicType

class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = "gemini-3-flash-preview"
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    MONGODB_URI: str
    DB_NAME: str = "damo"
    LANGFUSE_SECRET_KEY: str
    LANGFUSE_PUBLIC_KEY: str
    LANGFUSE_BASE_URL: str
    AWS_ENDPOINT_URL: str
    AWS_REGION: str
    AWS_BUCKET_NAME: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET: str
    LANGSMITH_API_KEY: str
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str

    KAFKA_BOOTSTRAP_SERVERS: str
    # 사용 토픽 (BE -> AI)
    KAFKA_RECOMMENDATION_REQUEST_TOPIC: str = TopicType.RECOMMENDATION_REQUEST.value
    KAFKA_RECOMMENDATION_RETRY_TOPIC: str = TopicType.RECOMMENDATION_RETRY.value
    KAFKA_PERSONA_REQUEST_TOPIC: str = TopicType.PERSONA_REQUEST.value
    KAFKA_OCR_REQUEST_TOPIC: str = TopicType.OCR_REQUEST.value
    KAFKA_FIX_REQUEST_TOPIC: str = TopicType.FIX_REQUEST.value
    # 사용 토픽 (AI -> BE)
    KAFKA_RECOMMENDATION_RESPONSE_TOPIC: str = TopicType.RECOMMENDATION_RESPONSE.value
    KAFKA_RECOMMENDATION_STREAMING_TOPIC: str = TopicType.RECOMMENDATION_STREAMING.value
    KAFKA_OCR_RESPONSE_TOPIC: str = TopicType.OCR_RESPONSE.value
    
    KAFKA_GROUP_ID: str = "ai-message-group"
    KAFKA_CLIENT_ID: str = f"ai-client-{uuid4()}"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

def get_settings() -> Settings:
    return Settings()