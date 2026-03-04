from __future__ import annotations

from rag_healthbot_server import db
from rag_healthbot_server.Models.ReportProcedure import (
    IReportProcedure,
    ReportProcedure,
)

from pydantic import validate_call
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError


@validate_call
def create_report_procedure(data: IReportProcedure) -> ReportProcedure:
    link = ReportProcedure(**data.model_dump())
    try:
        db.session.add(link)
        db.session.commit()
        db.session.refresh(link)
        return link
    except SQLAlchemyError:
        db.session.rollback()
        raise


@validate_call
def get_report_procedure(report_procedure_id: int) -> ReportProcedure | None:
    stmt = select(ReportProcedure).where(ReportProcedure.id == report_procedure_id)
    return db.session.scalar(stmt)


def list_report_procedures() -> list[ReportProcedure]:
    stmt = select(ReportProcedure).order_by(ReportProcedure.created_at.desc())
    return list(db.session.scalars(stmt).all())


@validate_call
def delete_report_procedure(report_procedure_id: int) -> bool:
    link = get_report_procedure(report_procedure_id)
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
def get_procedures_for_report(report_id: int) -> list[ReportProcedure]:
    stmt = (
        select(ReportProcedure)
        .where(ReportProcedure.report_id == report_id)
        .order_by(ReportProcedure.created_at.desc())
    )
    return list(db.session.scalars(stmt).all())


def update_report_procedure_fields(
    link_id: int, updates: dict
) -> ReportProcedure | None:
    """Patch arbitrary columns on a report_procedure join row."""
    link = get_report_procedure(link_id)
    if link is None:
        return None
    for key, value in updates.items():
        setattr(link, key, value)
    try:
        db.session.commit()
        db.session.refresh(link)
        return link
    except SQLAlchemyError:
        db.session.rollback()
        raise
