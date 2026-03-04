from __future__ import annotations

from rag_healthbot_server import db
from rag_healthbot_server.Models.Disease import IDisease, Disease

from pydantic import validate_call
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError


@validate_call
def create_disease(data: IDisease) -> Disease:
    disease = Disease(**data.model_dump())
    try:
        db.session.add(disease)
        db.session.commit()
        db.session.refresh(disease)
        return disease
    except SQLAlchemyError:
        db.session.rollback()
        raise


@validate_call
def get_disease(disease_id: int) -> Disease | None:
    stmt = select(Disease).where(Disease.id == disease_id)
    return db.session.scalar(stmt)


def list_diseases() -> list[Disease]:
    stmt = select(Disease).order_by(Disease.name.asc())
    return list(db.session.scalars(stmt).all())


@validate_call
def get_disease_by_name(name: str) -> Disease | None:
    normalized = (name or "").strip().lower()
    stmt = select(Disease).where(func.lower(Disease.name) == normalized)
    return db.session.scalar(stmt)


@validate_call
def get_disease_by_cui(cui: str) -> Disease | None:
    stmt = select(Disease).where(Disease.cui == cui)
    return db.session.scalar(stmt)


@validate_call
def delete_disease(disease_id: int) -> bool:
    disease = get_disease(disease_id)
    if disease is None:
        return False
    try:
        db.session.delete(disease)
        db.session.commit()
        return True
    except SQLAlchemyError:
        db.session.rollback()
        raise


def update_disease(disease_id: int, updates: dict[str, str | None]) -> Disease | None:
    disease = get_disease(disease_id)
    if disease is None:
        return None

    for key in (
        "name",
        "cui",
        "icd10_code",
        "confidence",
        "review_status",
        "review_notes",
        "candidates_json",
    ):
        if key in updates:
            setattr(disease, key, updates[key])

    try:
        db.session.commit()
        db.session.refresh(disease)
        return disease
    except SQLAlchemyError:
        db.session.rollback()
        raise
