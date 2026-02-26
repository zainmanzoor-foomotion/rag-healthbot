from ..db import Base
from sqlalchemy import DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from pydantic import BaseModel


class IReport(BaseModel):
    file_name: str
    summary: str
    extracted_text: str | None = None
    # Fingerprints for deduplication. `content_hash` should be based on raw file bytes.
    # `extracted_text_hash` should be based on OCR/extracted text.
    content_hash: str | None = None
    extracted_text_hash: str | None = None
    medications: list[int] = []


class Report(Base):
    __tablename__ = "report"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=True)

    content_hash: Mapped[str | None] = mapped_column(nullable=True, unique=True)
    extracted_text_hash: Mapped[str | None] = mapped_column(nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, default=datetime.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, default=datetime.now(), onupdate=datetime.now()
    )
    medications = relationship("ReportMedication", back_populates="report")
