from __future__ import annotations

from rag_healthbot_server import db
from rag_healthbot_server.Models.Medication import IMedication, Medication

from pydantic import validate_call
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError


@validate_call
def create_medication(data: IMedication) -> Medication:
    medication = Medication(**data.model_dump())
    try:
        db.session.add(medication)
        db.session.commit()
        db.session.refresh(medication)
        return medication
    except SQLAlchemyError:
        db.session.rollback()
        raise


@validate_call
def get_medication(medication_id: int) -> Medication | None:
    stmt = select(Medication).where(Medication.id == medication_id)
    return db.session.scalar(stmt)


def list_medications() -> list[Medication]:
    stmt = select(Medication).order_by(Medication.name.asc())
    return list(db.session.scalars(stmt).all())


@validate_call
def delete_medication(medication_id: int) -> bool:
    medication = get_medication(medication_id)
    if medication is None:
        return False
    try:
        db.session.delete(medication)
        db.session.commit()
        return True
    except SQLAlchemyError:
        db.session.rollback()
        raise


@validate_call
def update_medication(medication_id: int, data: IMedication) -> Medication | None:
    medication = get_medication(medication_id)
    if medication is None:
        return None

    payload = data.model_dump()
    for key in ("name", "rxnorm_code", "ndc_code"):
        if key in payload:
            setattr(medication, key, payload[key])

    try:
        db.session.commit()
        db.session.refresh(medication)
        return medication
    except SQLAlchemyError:
        db.session.rollback()
        raise
