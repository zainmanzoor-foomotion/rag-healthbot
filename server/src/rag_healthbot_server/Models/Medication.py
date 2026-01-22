from ..db import Base
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from pydantic import BaseModel


class IMedication(BaseModel):
    name: str
    rxnorm_code: str | None = None
    ndc_code: str | None = None


class Medication(Base):
    __tablename__ = "medication"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    rxnorm_code: Mapped[str] = mapped_column(nullable=True, unique=True)
    ndc_code: Mapped[str] = mapped_column(nullable=True, unique=True)

    reports = relationship("ReportMedication", back_populates="medication")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, default=datetime.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, default=datetime.now(), onupdate=datetime.now()
    )
