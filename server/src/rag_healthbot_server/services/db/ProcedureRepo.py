from __future__ import annotations

from rag_healthbot_server import db
from rag_healthbot_server.Models.Procedure import IProcedure, Procedure

from pydantic import validate_call
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError


@validate_call
def create_procedure(data: IProcedure) -> Procedure:
    procedure = Procedure(**data.model_dump())
    try:
        db.session.add(procedure)
        db.session.commit()
        db.session.refresh(procedure)
        return procedure
    except SQLAlchemyError:
        db.session.rollback()
        raise


@validate_call
def get_procedure(procedure_id: int) -> Procedure | None:
    stmt = select(Procedure).where(Procedure.id == procedure_id)
    return db.session.scalar(stmt)


def list_procedures() -> list[Procedure]:
    stmt = select(Procedure).order_by(Procedure.name.asc())
    return list(db.session.scalars(stmt).all())


@validate_call
def get_procedure_by_name(name: str) -> Procedure | None:
    normalized = (name or "").strip().lower()
    stmt = select(Procedure).where(func.lower(Procedure.name) == normalized)
    return db.session.scalar(stmt)


@validate_call
def get_procedure_by_cui(cui: str) -> Procedure | None:
    stmt = select(Procedure).where(Procedure.cui == cui)
    return db.session.scalar(stmt)


@validate_call
def delete_procedure(procedure_id: int) -> bool:
    procedure = get_procedure(procedure_id)
    if procedure is None:
        return False
    try:
        db.session.delete(procedure)
        db.session.commit()
        return True
    except SQLAlchemyError:
        db.session.rollback()
        raise


def update_procedure(
    procedure_id: int, updates: dict[str, str | None]
) -> Procedure | None:
    procedure = get_procedure(procedure_id)
    if procedure is None:
        return None

    for key in (
        "name",
        "cui",
        "cpt_code",
        "confidence",
        "review_status",
        "review_notes",
        "candidates_json",
    ):
        if key in updates:
            setattr(procedure, key, updates[key])

    try:
        db.session.commit()
        db.session.refresh(procedure)
        return procedure
    except SQLAlchemyError:
        db.session.rollback()
        raise
