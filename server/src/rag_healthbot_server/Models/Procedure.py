from ..db import Base
from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from pydantic import BaseModel


class IProcedure(BaseModel):
    name: str
    cui: str | None = None
    cpt_code: str | None = None
    confidence: float | None = None
    review_status: str = "pending_review"
    review_notes: str | None = None
    candidates_json: str | None = None


class Procedure(Base):
    __tablename__ = "procedure"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    cui: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    cpt_code: Mapped[str | None] = mapped_column(String, nullable=True)

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="pending_review"
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidates_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    reports = relationship("ReportProcedure", back_populates="procedure")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )
