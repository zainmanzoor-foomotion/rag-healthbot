from ..db import Base
from sqlalchemy import DateTime, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from pydantic import BaseModel
from pgvector.sqlalchemy import Vector
from ..config import settings


class ICodeEmbedding(BaseModel):
    code: str
    code_system: str  # "icd10" | "cpt"
    description: str
    embedding: list[float]


class CodeEmbedding(Base):
    """
    Stores vector embeddings for ICD-10-CM and CPT code descriptions.
    Used for semantic KB search during the multi-layer resolution pipeline.
    """

    __tablename__ = "code_embedding"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    code: Mapped[str] = mapped_column(String(20), nullable=False)
    code_system: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # "icd10" or "cpt"
    description: Mapped[str] = mapped_column(Text, nullable=False)

    embedding: Mapped[Vector] = mapped_column(
        Vector(settings.vector_dimension), nullable=False
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    __table_args__ = (
        Index("uq_code_system_code", "code_system", "code", unique=True),
        Index("idx_code_system", "code_system"),
        Index(
            "idx_code_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
