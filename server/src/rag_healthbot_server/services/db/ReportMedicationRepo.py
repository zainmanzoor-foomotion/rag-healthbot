from __future__ import annotations

from rag_healthbot_server import db
from rag_healthbot_server.Models.ReportMedication import (
    IReportMedication,
    ReportMedication,
)

from pydantic import validate_call
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError


@validate_call
def create_report_medication(data: IReportMedication) -> ReportMedication:
    link = ReportMedication(**data.model_dump())
    try:
        db.session.add(link)
        db.session.commit()
        db.session.refresh(link)
        return link
    except SQLAlchemyError:
        db.session.rollback()
        raise


@validate_call
def get_report_medication(report_medication_id: int) -> ReportMedication | None:
    stmt = select(ReportMedication).where(ReportMedication.id == report_medication_id)
    return db.session.scalar(stmt)


def list_report_medications() -> list[ReportMedication]:
    stmt = select(ReportMedication).order_by(ReportMedication.created_at.desc())
    return list(db.session.scalars(stmt).all())


@validate_call
def delete_report_medication(report_medication_id: int) -> bool:
    link = get_report_medication(report_medication_id)
    if link is None:
        return False
    try:
        db.session.delete(link)
        db.session.commit()
        return True
    except SQLAlchemyError:
        db.session.rollback()
        raise


@validate_call
def update_report_medication(
    report_medication_id: int, data: IReportMedication
) -> ReportMedication | None:
    link = get_report_medication(report_medication_id)
    if link is None:
        return None

    fields_set = getattr(data, "model_fields_set", set())
    if "report_id" in fields_set:
        link.report_id = data.report_id
    if "medication_id" in fields_set:
        link.medication_id = data.medication_id
    if "dosage" in fields_set:
        link.dosage = data.dosage
    if "frequency" in fields_set:
        link.frequency = data.frequency
    if "start_date" in fields_set:
        link.start_date = data.start_date
    if "end_date" in fields_set:
        link.end_date = data.end_date
    if "purpose" in fields_set:
        link.purpose = data.purpose

    try:
        db.session.commit()
        db.session.refresh(link)
        return link
    except SQLAlchemyError:
        db.session.rollback()
        raise
