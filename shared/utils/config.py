from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = "gemini-3-flash-preview"
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = ""
    MONGODB_URI: str
    DB_NAME: str = "damo"
    LOCAL_MODEL: str = ""
    LOCAL_BASE_URL: str = ""
    LOCAL_API_KEY: str = ""
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
    RUNPOD_API_KEY: str = ""
    RUNPOD_API_URL: str = ""
    GOOGLE_CREDENTIALS_JSON: str = ""
    
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_GROUP_ID: str = "damo-ai-dev"
    KAFKA_CLIENT_ID: str = "damo-ai-dev-gateway-client"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


def get_settings() -> Settings:
    return settings
