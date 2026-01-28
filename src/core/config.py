from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MONGODB_URI: str
    DB_NAME: str = "damo"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
