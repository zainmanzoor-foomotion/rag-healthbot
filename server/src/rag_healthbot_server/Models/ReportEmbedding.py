from ..db import Base
from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from pydantic import BaseModel
from pgvector.sqlalchemy import Vector
from ..config import settings
from typing import Annotated


def validate_vector_dimension(v: list[float]) -> list[float]:
    expected_dim = settings.vector_dimension
    if len(v) != expected_dim:
        raise ValueError(f"Vector dimension must be {expected_dim}, but got {len(v)}")
    return v


PgVector = Annotated[list[float], validate_vector_dimension]


class IReportEmbedding(BaseModel):
    text: str
    embedding: PgVector


class ReportEmbedding(Base):
    __tablename__ = "report_embedding"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("report.id", ondelete="CASCADE"), nullable=False
    )

    chunk_index: Mapped[int] = mapped_column(nullable=False)
    text: Mapped[Text] = mapped_column(Text, nullable=False)
    embedding: Mapped[Vector] = mapped_column(
        Vector(settings.vector_dimension), nullable=False
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, default=datetime.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, default=datetime.now(), onupdate=datetime.now()
    )

    __table_args__ = (
        UniqueConstraint("report_id", "chunk_index", name="uq_report_chunk"),
        Index("idx_report_id", "report_id"),
        Index(
            "idx_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
