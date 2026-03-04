from ..db import Base
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from pydantic import BaseModel


class IReportProcedure(BaseModel):
    report_id: int
    procedure_id: int
    date_performed: datetime | None = None
    body_site: str | None = None
    outcome: str | None = None
    coding_confidence: float | None = None
    review_status: str = "pending_review"
    review_notes: str | None = None
    candidates_json: str | None = None


class ReportProcedure(Base):
    __tablename__ = "report_procedure"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("report.id", ondelete="CASCADE"), nullable=False
    )
    procedure_id: Mapped[int] = mapped_column(
        ForeignKey("procedure.id"), nullable=False
    )

    date_performed: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    body_site: Mapped[str | None] = mapped_column(nullable=True)
    outcome: Mapped[str | None] = mapped_column(nullable=True)

    # Per-report review tracking (coding is scoped to this report occurrence)
    coding_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="pending_review"
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidates_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, default=datetime.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, default=datetime.now(), onupdate=datetime.now()
    )

    report = relationship("Report", back_populates="procedures")
    procedure = relationship("Procedure", back_populates="reports")
