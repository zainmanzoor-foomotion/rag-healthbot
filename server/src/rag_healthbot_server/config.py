from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    redis_url: str = Field(default="", validation_alias="REDIS_URL")
    database_url: str = Field(default="", validation_alias="DATABASE_CONNECTION_MAIN")

    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")

    llm_model: str = Field(default="openai/gpt-oss-120b", validation_alias="LLM_MODEL")
    ollama_host: str = Field(
        default="",
        validation_alias=AliasChoices("OLLAMA_HOST", "OLLAMA_EMBED_HOST"),
    )
    ollama_embed_model: str = Field(default="", validation_alias="OLLAMA_MODEL")
    groq_ocr_model: str = Field(default="", validation_alias="GROQ_OCR_MODEL")
    vector_dimension: int = Field(default=0, validation_alias="VECTOR_DIMENSION")

    prometheus_multiproc_dir: str = Field(
        default="/tmp/healthrag_prometheus", validation_alias="PROMETHEUS_MULTIPROC_DIR"
    )

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env.development"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
