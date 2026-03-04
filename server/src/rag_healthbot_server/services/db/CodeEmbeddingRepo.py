from __future__ import annotations

from rag_healthbot_server import db
from rag_healthbot_server.Models.CodeEmbedding import CodeEmbedding

from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError


def upsert_code_embeddings(
    rows: list[dict],
) -> int:
    """
    Bulk-insert code embeddings.  Each dict must have keys:
    code, code_system, description, embedding.
    Deletes existing rows for the same (code_system, code) before inserting.
    Returns the number of rows inserted.
    """
    if not rows:
        return 0

    try:
        # Collect codes per system for batch delete
        codes_by_system: dict[str, list[str]] = {}
        for r in rows:
            codes_by_system.setdefault(r["code_system"], []).append(r["code"])

        for system, codes in codes_by_system.items():
            db.session.execute(
                delete(CodeEmbedding).where(
                    CodeEmbedding.code_system == system,
                    CodeEmbedding.code.in_(codes),
                )
            )

        objects = [CodeEmbedding(**r) for r in rows]
        db.session.add_all(objects)
        db.session.commit()
        return len(objects)
    except SQLAlchemyError:
        db.session.rollback()
        raise


def search_code_embeddings(
    query_embedding: list[float],
    code_system: str,
    top_k: int = 10,
) -> list[tuple[CodeEmbedding, float]]:
    """
    Semantic search over code embeddings filtered by code_system.
    Returns list of (CodeEmbedding, cosine_distance) tuples sorted by
    ascending distance (best match first).
    """
    if top_k <= 0:
        return []

    distance = CodeEmbedding.embedding.cosine_distance(query_embedding)
    stmt = (
        select(CodeEmbedding, distance.label("distance"))
        .where(CodeEmbedding.code_system == code_system)
        .order_by(distance.asc())
        .limit(int(top_k))
    )
    results = db.session.execute(stmt).all()
    return [(row[0], float(row[1])) for row in results]


def count_code_embeddings(code_system: str | None = None) -> int:
    """Count code embeddings, optionally filtered by code_system."""
    stmt = select(CodeEmbedding)
    if code_system:
        stmt = stmt.where(CodeEmbedding.code_system == code_system)
    from sqlalchemy import func

    count_stmt = select(func.count()).select_from(stmt.subquery())
    return db.session.scalar(count_stmt) or 0


def delete_all_code_embeddings(code_system: str | None = None) -> int:
    """Delete all code embeddings, optionally filtered by code_system."""
    try:
        stmt = delete(CodeEmbedding)
        if code_system:
            stmt = stmt.where(CodeEmbedding.code_system == code_system)
        result = db.session.execute(stmt)
        db.session.commit()
        return result.rowcount  # type: ignore[return-value]
    except SQLAlchemyError:
        db.session.rollback()
        raise
