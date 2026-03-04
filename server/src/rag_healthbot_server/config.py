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

    # ── scispaCy / UMLS settings ──────────────────────────────────
    scispacy_model: str = Field(
        default="en_core_sci_sm", validation_alias="SCISPACY_MODEL"
    )
    # Specialised NER models (BC5CDR → chemicals + diseases, BioNLP → procedures)
    ner_bc5cdr_model: str = Field(
        default="en_ner_bc5cdr_md", validation_alias="NER_BC5CDR_MODEL"
    )
    ner_bionlp_model: str = Field(
        default="en_ner_bionlp13cg_md", validation_alias="NER_BIONLP_MODEL"
    )
    umls_linker_threshold: float = Field(
        default=0.85, validation_alias="UMLS_LINKER_THRESHOLD"
    )
    umls_api_key: str = Field(default="", validation_alias="UMLS_API_KEY")

    # ── Local code-file paths for validation + refinement ─────────
    icd10_file: str = Field(default="", validation_alias="ICD10_FILE")
    cpt_file: str = Field(default="", validation_alias="CPT_FILE")

    # ── Confidence / review settings ──────────────────────────────
    auto_accept_threshold: float = Field(
        default=0.85, validation_alias="AUTO_ACCEPT_THRESHOLD"
    )

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
