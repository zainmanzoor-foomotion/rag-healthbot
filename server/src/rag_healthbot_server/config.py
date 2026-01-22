from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    redis_url: str = Field(default="", validation_alias="REDIS_URL")
    database_url: str = Field(default="", validation_alias="DATABASE_CONNECTION_MAIN")

    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")

    llm_model: str = Field(default="openai/gpt-oss-120b", validation_alias="LLM_MODEL")

    prometheus_multiproc_dir: str = Field(
        default="/tmp/mar_prometheus", validation_alias="PROMETHEUS_MULTIPROC_DIR"
    )

    model_config = SettingsConfigDict(
        env_file=".env.development",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
