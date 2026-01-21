from ..db import Base
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from pydantic import BaseModel


class ReportMedication(Base):
    __tablename__ = "report_medication"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("report.id", ondelete="CASCADE"), nullable=False
    )
    medication_id: Mapped[int] = mapped_column(
        ForeignKey("medication.id"), nullable=False
    )

    dosage: Mapped[str] = mapped_column(nullable=True)
    frequency: Mapped[str] = mapped_column(nullable=True)
    start_date: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    purpose: Mapped[str] = mapped_column(nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, default=datetime.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, default=datetime.now(), onupdate=datetime.now()
    )

    report = relationship("Report", back_populates="medications")
    medication = relationship("Medication", back_populates="reports")
