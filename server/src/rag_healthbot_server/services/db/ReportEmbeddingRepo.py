from __future__ import annotations

from rag_healthbot_server import db
from rag_healthbot_server.Models.ReportEmbedding import (
    IReportEmbedding,
    ReportEmbedding,
)

from pydantic import validate_call, BaseModel
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError


class IReportEmbeddings(BaseModel):
    report_id: int
    texts: list[str]
    embeddings: list[list[float]]


@validate_call
def create_report_embeddings(data: IReportEmbeddings) -> list[ReportEmbedding]:
    payload = data.model_dump()
    report_id = payload.pop("report_id")
    embeddings = payload.pop("embeddings")
    texts = payload.pop("texts")
    created_links = []
    try:
        for embedding, text in zip(embeddings, texts):
            link = ReportEmbedding(report_id=report_id, embedding=embedding, text=text)
            db.session.add(link)
            created_links.append(link)

        db.session.commit()
        for link in created_links:
            db.session.refresh(link)
        return created_links
    except SQLAlchemyError:
        db.session.rollback()
        raise


@validate_call
def get_report_embedding(report_embedding_id: int) -> ReportEmbedding | None:
    stmt = select(ReportEmbedding).where(ReportEmbedding.id == report_embedding_id)
    return db.session.scalar(stmt)


@validate_call
def list_report_embeddings(report_id: int) -> list[ReportEmbedding]:
    stmt = select(ReportEmbedding).where(ReportEmbedding.report_id == report_id)
    return list(db.session.scalars(stmt).all())


@validate_call
def delete_report_embedding(report_embedding_id: int) -> bool:
    link = get_report_embedding(report_embedding_id)
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
def delete_report_embeddings_by_report_id(report_id: int) -> int:
    stmt = select(ReportEmbedding).where(ReportEmbedding.report_id == report_id)
    links = list(db.session.scalars(stmt).all())
    if not links:
        return 0
    try:
        for link in links:
            db.session.delete(link)
        db.session.commit()
        return len(links)
    except SQLAlchemyError:
        db.session.rollback()
        raise


@validate_call
def update_report_embedding(
    report_embedding_id: int, data: IReportEmbedding
) -> ReportEmbedding | None:
    link = get_report_embedding(report_embedding_id)
    if link is None:
        return None

    fields_set = getattr(data, "model_fields_set", set())
    if "report_id" in fields_set:
        link.report_id = data.report_id
    if "embedding" in fields_set:
        link.embedding = data.embedding
    if "text" in fields_set:
        link.text = data.text

    try:
        db.session.commit()
        db.session.refresh(link)
        return link
    except SQLAlchemyError:
        db.session.rollback()
        raise
