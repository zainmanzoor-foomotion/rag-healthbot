from __future__ import annotations

from rag_healthbot_server import db
from rag_healthbot_server.Models.ReportDisease import (
    IReportDisease,
    ReportDisease,
)

from pydantic import validate_call
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError


@validate_call
def create_report_disease(data: IReportDisease) -> ReportDisease:
    link = ReportDisease(**data.model_dump())
    try:
        db.session.add(link)
        db.session.commit()
        db.session.refresh(link)
        return link
    except SQLAlchemyError:
        db.session.rollback()
        raise


@validate_call
def get_report_disease(report_disease_id: int) -> ReportDisease | None:
    stmt = select(ReportDisease).where(ReportDisease.id == report_disease_id)
    return db.session.scalar(stmt)


def list_report_diseases() -> list[ReportDisease]:
    stmt = select(ReportDisease).order_by(ReportDisease.created_at.desc())
    return list(db.session.scalars(stmt).all())


@validate_call
def delete_report_disease(report_disease_id: int) -> bool:
    link = get_report_disease(report_disease_id)
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
def get_diseases_for_report(report_id: int) -> list[ReportDisease]:
    stmt = (
        select(ReportDisease)
        .where(ReportDisease.report_id == report_id)
        .order_by(ReportDisease.created_at.desc())
    )
    return list(db.session.scalars(stmt).all())


def update_report_disease_fields(link_id: int, updates: dict) -> ReportDisease | None:
    """Patch arbitrary columns on a report_disease join row."""
    link = get_report_disease(link_id)
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
