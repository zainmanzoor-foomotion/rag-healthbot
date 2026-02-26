from __future__ import annotations

from rag_healthbot_server import db
from rag_healthbot_server.Models.Report import IReport, Report
from rag_healthbot_server.Models.ReportMedication import ReportMedication

from pydantic import validate_call
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError


def _sync_report_medications(report: Report, medication_ids: list[int]) -> None:
    desired_ids = set(medication_ids)
    existing_links = list(report.medications or [])
    existing_ids = {link.medication_id for link in existing_links}

    to_remove = [
        link for link in existing_links if link.medication_id not in desired_ids
    ]
    to_add = list(desired_ids - existing_ids)

    for link in to_remove:
        db.session.delete(link)
    for medication_id in to_add:
        db.session.add(
            ReportMedication(report_id=report.id, medication_id=medication_id)
        )


@validate_call
def create_report(data: IReport) -> Report:
    payload = data.model_dump()
    medication_ids = payload.pop("medications", [])

    report = Report(**payload)
    try:
        db.session.add(report)
        db.session.flush()  # get report.id for link rows
        if medication_ids:
            _sync_report_medications(report, medication_ids)
        db.session.commit()
        db.session.refresh(report)
        return report
    except SQLAlchemyError:
        db.session.rollback()
        raise


@validate_call
def get_report(report_id: int) -> Report | None:
    stmt = select(Report).where(Report.id == report_id)
    return db.session.scalar(stmt)


@validate_call
def get_report_by_content_hash(content_hash: str) -> Report | None:
    stmt = (
        select(Report)
        .where(Report.content_hash == content_hash)
        .options(
            selectinload(Report.medications).selectinload(ReportMedication.medication)
        )
    )
    return db.session.scalar(stmt)


@validate_call
def get_report_by_extracted_text_hash(extracted_text_hash: str) -> Report | None:
    stmt = (
        select(Report)
        .where(Report.extracted_text_hash == extracted_text_hash)
        .options(
            selectinload(Report.medications).selectinload(ReportMedication.medication)
        )
    )
    return db.session.scalar(stmt)


def list_reports() -> list[Report]:
    stmt = select(Report).order_by(Report.created_at.desc())
    return list(db.session.scalars(stmt).all())


@validate_call
def delete_report(report_id: int) -> bool:
    report = get_report(report_id)
    if report is None:
        return False
    try:
        db.session.delete(report)
        db.session.commit()
        return True
    except SQLAlchemyError:
        db.session.rollback()
        raise


@validate_call
def update_report(report_id: int, data: IReport) -> Report | None:
    report = get_report(report_id)
    if report is None:
        return None

    fields_set = getattr(data, "model_fields_set", set())

    if "file_name" in fields_set:
        report.file_name = data.file_name
    if "summary" in fields_set:
        report.summary = data.summary
    if "extracted_text" in fields_set:
        report.extracted_text = data.extracted_text
    if "content_hash" in fields_set:
        report.content_hash = data.content_hash
    if "extracted_text_hash" in fields_set:
        report.extracted_text_hash = data.extracted_text_hash

    try:
        if "medications" in fields_set:
            _sync_report_medications(report, data.medications)
        db.session.commit()
        db.session.refresh(report)
        return report
    except SQLAlchemyError:
        db.session.rollback()
        raise
