"""Review queue API — human-in-the-loop for uncertain entity codes.

Endpoints:
    GET    /api/review/queue          — paginated list of pending-review entities
    GET    /api/review/{type}/{id}    — single entity details + candidates
    PATCH  /api/review/{type}/{id}    — approve / reject / update code
    GET    /api/review/stats          — summary counts per entity type
"""

from __future__ import annotations

import json
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from rag_healthbot_server.services.db.DiseaseRepo import (
    get_disease,
    list_diseases,
    update_disease,
)
from rag_healthbot_server.services.db.ProcedureRepo import (
    get_procedure,
    list_procedures,
    update_procedure,
)
from rag_healthbot_server.services.db.MedicationRepo import (
    get_medication,
    list_medications,
    update_medication,
)
from rag_healthbot_server.services.db.ReportDiseaseRepo import (
    get_diseases_for_report,
    update_report_disease_fields,
)
from rag_healthbot_server.services.db.ReportMedicationRepo import (
    get_medications_for_report,
    update_report_medication_fields,
)
from rag_healthbot_server.services.db.ReportProcedureRepo import (
    get_procedures_for_report,
    update_report_procedure_fields,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/review", tags=["review"])

EntityType = Literal["disease", "procedure", "medication"]


# ── Response schemas ────────────────────────────────────────────────


class ReviewItem(BaseModel):
    id: int
    entity_type: str
    name: str
    cui: str | None = None
    code: str | None = None  # icd10_code / cpt_code
    confidence: float | None = None
    review_status: str = "pending_review"
    review_notes: str | None = None
    candidates: list[dict] | None = None
    # Per-report fields (populated for by-report endpoints)
    link_id: int | None = None
    report_id: int | None = None


class ReviewStats(BaseModel):
    pending_diseases: int = 0
    pending_procedures: int = 0
    pending_medications: int = 0
    total_pending: int = 0
    accepted_diseases: int = 0
    accepted_procedures: int = 0
    accepted_medications: int = 0


class ReviewAction(BaseModel):
    """Payload for PATCH — reviewer decision."""

    action: Literal["accept", "reject", "update"]
    cui: str | None = None
    code: str | None = None  # new ICD-10 / CPT code chosen by reviewer
    review_notes: str | None = None


# ── GET /api/review/stats ──────────────────────────────────────────


@router.get("/stats", response_model=ReviewStats)
def get_review_stats():
    """Summary counts of pending vs accepted entities."""
    diseases = list_diseases()
    procedures = list_procedures()
    medications = list_medications()

    pending_d = sum(
        1 for d in diseases if getattr(d, "review_status", "") == "pending_review"
    )
    pending_p = sum(
        1 for p in procedures if getattr(p, "review_status", "") == "pending_review"
    )
    pending_m = sum(
        1 for m in medications if getattr(m, "review_status", "") == "pending_review"
    )

    accepted_d = sum(
        1 for d in diseases if getattr(d, "review_status", "") == "accepted"
    )
    accepted_p = sum(
        1 for p in procedures if getattr(p, "review_status", "") == "accepted"
    )
    accepted_m = sum(
        1 for m in medications if getattr(m, "review_status", "") == "accepted"
    )

    return ReviewStats(
        pending_diseases=pending_d,
        pending_procedures=pending_p,
        pending_medications=pending_m,
        total_pending=pending_d + pending_p + pending_m,
        accepted_diseases=accepted_d,
        accepted_procedures=accepted_p,
        accepted_medications=accepted_m,
    )


# ── GET /api/review/queue ──────────────────────────────────────────


@router.get("/queue", response_model=list[ReviewItem])
def get_review_queue(
    entity_type: EntityType | None = Query(None, description="Filter by entity type"),
    status: str = Query("pending_review", description="Filter by review_status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Paginated list of entities matching the given review status."""
    items: list[ReviewItem] = []

    if entity_type is None or entity_type == "disease":
        for d in list_diseases():
            if getattr(d, "review_status", "") == status:
                cands = _parse_candidates(getattr(d, "candidates_json", None))
                items.append(
                    ReviewItem(
                        id=d.id,
                        entity_type="disease",
                        name=d.name,
                        cui=d.cui,
                        code=d.icd10_code,
                        confidence=getattr(d, "confidence", None),
                        review_status=getattr(d, "review_status", "pending_review"),
                        review_notes=getattr(d, "review_notes", None),
                        candidates=cands,
                    )
                )

    if entity_type is None or entity_type == "procedure":
        for p in list_procedures():
            if getattr(p, "review_status", "") == status:
                cands = _parse_candidates(getattr(p, "candidates_json", None))
                items.append(
                    ReviewItem(
                        id=p.id,
                        entity_type="procedure",
                        name=p.name,
                        cui=p.cui,
                        code=p.cpt_code,
                        confidence=getattr(p, "confidence", None),
                        review_status=getattr(p, "review_status", "pending_review"),
                        review_notes=getattr(p, "review_notes", None),
                        candidates=cands,
                    )
                )

    if entity_type is None or entity_type == "medication":
        for m in list_medications():
            if getattr(m, "review_status", "") == status:
                items.append(
                    ReviewItem(
                        id=m.id,
                        entity_type="medication",
                        name=m.name,
                        cui=m.cui,
                        code=None,
                        confidence=getattr(m, "confidence", None),
                        review_status=getattr(m, "review_status", "pending_review"),
                        review_notes=getattr(m, "review_notes", None),
                    )
                )

    # Sort by confidence ascending (least confident first)
    items.sort(key=lambda x: x.confidence or 0.0)
    return items[offset : offset + limit]


# ── GET /api/review/by-report/{report_id} ─────────────────────────


@router.get("/by-report/{report_id}", response_model=list[ReviewItem])
def get_review_queue_for_report(
    report_id: int,
    status: str | None = Query(
        None, description="Filter by review_status; omit for all"
    ),
):
    """Return all reviewable entity occurrences for a specific report.

    Each item includes the join-row ``link_id`` so that the admin panel can
    PATCH the exact occurrence rather than the global canonical entity.
    """
    items: list[ReviewItem] = []

    for link in get_diseases_for_report(report_id):
        rs = getattr(link, "review_status", "pending_review")
        if status is not None and rs != status:
            continue
        dis = getattr(link, "disease", None)
        if dis is None:
            continue
        cands = _parse_candidates(getattr(link, "candidates_json", None))
        items.append(
            ReviewItem(
                id=dis.id,
                entity_type="disease",
                name=dis.name,
                cui=dis.cui,
                code=dis.icd10_code,
                confidence=getattr(link, "coding_confidence", None),
                review_status=rs,
                review_notes=getattr(link, "review_notes", None),
                candidates=cands,
                link_id=link.id,
                report_id=report_id,
            )
        )

    for link in get_medications_for_report(report_id):
        rs = getattr(link, "review_status", "pending_review")
        if status is not None and rs != status:
            continue
        med = getattr(link, "medication", None)
        if med is None:
            continue
        items.append(
            ReviewItem(
                id=med.id,
                entity_type="medication",
                name=med.name,
                cui=med.cui,
                code=None,
                confidence=getattr(link, "coding_confidence", None),
                review_status=rs,
                review_notes=getattr(link, "review_notes", None),
                candidates=None,
                link_id=link.id,
                report_id=report_id,
            )
        )

    for link in get_procedures_for_report(report_id):
        rs = getattr(link, "review_status", "pending_review")
        if status is not None and rs != status:
            continue
        proc = getattr(link, "procedure", None)
        if proc is None:
            continue
        cands = _parse_candidates(getattr(link, "candidates_json", None))
        items.append(
            ReviewItem(
                id=proc.id,
                entity_type="procedure",
                name=proc.name,
                cui=proc.cui,
                code=proc.cpt_code,
                confidence=getattr(link, "coding_confidence", None),
                review_status=rs,
                review_notes=getattr(link, "review_notes", None),
                candidates=cands,
                link_id=link.id,
                report_id=report_id,
            )
        )

    # Sort: pending first, then by confidence ascending
    items.sort(key=lambda x: (x.review_status != "pending_review", x.confidence or 0.0))
    return items


# ── PATCH /api/review/by-report/{report_id}/{type}/{link_id} ──────


@router.patch(
    "/by-report/{report_id}/{entity_type}/{link_id}", response_model=ReviewItem
)
def review_entity_for_report(
    report_id: int,
    entity_type: EntityType,
    link_id: int,
    body: ReviewAction,
):
    """Accept, reject, or update a single entity occurrence within a report.

    - Updates ``review_status`` / ``coding_confidence`` / ``review_notes`` on
      the join row (report-scoped).
    - On ``accept`` / ``update``: also writes the confirmed code back to the
      canonical entity row so the ICD-10/CPT is stored globally once.
    """
    join_updates: dict[str, str | float | None] = {}
    canonical_updates: dict[str, str | float | None] = {}

    if body.action == "accept":
        join_updates["review_status"] = "accepted"
        join_updates["coding_confidence"] = 1.0
        if body.code:
            canonical_updates[_code_field(entity_type)] = body.code
        if body.cui:
            canonical_updates["cui"] = body.cui
    elif body.action == "reject":
        join_updates["review_status"] = "rejected"
        join_updates["coding_confidence"] = 0.0
    elif body.action == "update":
        join_updates["review_status"] = "accepted"
        join_updates["coding_confidence"] = 1.0
        if body.code:
            canonical_updates[_code_field(entity_type)] = body.code
        if body.cui:
            canonical_updates["cui"] = body.cui

    if body.review_notes is not None:
        join_updates["review_notes"] = body.review_notes

    # Update join row
    updated_link = _update_join_row(entity_type, link_id, join_updates)
    if updated_link is None:
        raise HTTPException(404, f"{entity_type} link {link_id} not found")

    # Update canonical entity (code/cui only)
    entity_id = _entity_id_from_link(entity_type, updated_link)
    if entity_id is not None and canonical_updates:
        _update_entity(entity_type, entity_id, canonical_updates)

    entity = _get_entity(entity_type, entity_id) if entity_id else None

    logger.info(
        "Review %s %s/link=%d report=%d: status=%s",
        body.action,
        entity_type,
        link_id,
        report_id,
        join_updates.get("review_status"),
    )

    return ReviewItem(
        id=entity_id or 0,
        entity_type=entity_type,
        name=entity.name if entity else "",
        cui=entity.cui if entity else None,
        code=_get_entity_code(entity_type, entity) if entity else None,
        confidence=getattr(updated_link, "coding_confidence", None),
        review_status=getattr(updated_link, "review_status", "pending_review"),
        review_notes=getattr(updated_link, "review_notes", None),
        candidates=_parse_candidates(getattr(updated_link, "candidates_json", None)),
        link_id=link_id,
        report_id=report_id,
    )


# ── GET /api/review/{type}/{id} ────────────────────────────────────


@router.get("/{entity_type}/{entity_id}", response_model=ReviewItem)
def get_review_item(entity_type: EntityType, entity_id: int):
    """Retrieve a single entity with its candidate codes."""
    entity = _get_entity(entity_type, entity_id)
    if entity is None:
        raise HTTPException(404, f"{entity_type} {entity_id} not found")

    code = None
    cands = None
    if entity_type == "disease":
        code = entity.icd10_code
        cands = _parse_candidates(getattr(entity, "candidates_json", None))
    elif entity_type == "procedure":
        code = entity.cpt_code
        cands = _parse_candidates(getattr(entity, "candidates_json", None))

    return ReviewItem(
        id=entity.id,
        entity_type=entity_type,
        name=entity.name,
        cui=entity.cui,
        code=code,
        confidence=getattr(entity, "confidence", None),
        review_status=getattr(entity, "review_status", "pending_review"),
        review_notes=getattr(entity, "review_notes", None),
        candidates=cands,
    )


# ── PATCH /api/review/{type}/{id} ─────────────────────────────────


@router.patch("/{entity_type}/{entity_id}", response_model=ReviewItem)
def review_entity(entity_type: EntityType, entity_id: int, body: ReviewAction):
    """Accept, reject, or update the code for an entity."""
    entity = _get_entity(entity_type, entity_id)
    if entity is None:
        raise HTTPException(404, f"{entity_type} {entity_id} not found")

    updates: dict[str, str | float | None] = {}

    if body.action == "accept":
        updates["review_status"] = "accepted"
        if body.code:
            updates[_code_field(entity_type)] = body.code
        if body.cui:
            updates["cui"] = body.cui
        updates["confidence"] = 1.0  # human-confirmed
    elif body.action == "reject":
        updates["review_status"] = "rejected"
        updates[_code_field(entity_type)] = None
        updates["cui"] = None
        updates["confidence"] = 0.0
    elif body.action == "update":
        if body.code:
            updates[_code_field(entity_type)] = body.code
        if body.cui:
            updates["cui"] = body.cui
        updates["review_status"] = "accepted"
        updates["confidence"] = 1.0

    if body.review_notes is not None:
        updates["review_notes"] = body.review_notes

    updated = _update_entity(entity_type, entity_id, updates)
    if updated is None:
        raise HTTPException(500, "Update failed")

    logger.info(
        "Review %s %s/%d: status=%s code=%s",
        body.action,
        entity_type,
        entity_id,
        updates.get("review_status"),
        updates.get(_code_field(entity_type)),
    )

    code = None
    cands = None
    if entity_type == "disease":
        code = updated.icd10_code
        cands = _parse_candidates(getattr(updated, "candidates_json", None))
    elif entity_type == "procedure":
        code = updated.cpt_code
        cands = _parse_candidates(getattr(updated, "candidates_json", None))

    return ReviewItem(
        id=updated.id,
        entity_type=entity_type,
        name=updated.name,
        cui=updated.cui,
        code=code,
        confidence=getattr(updated, "confidence", None),
        review_status=getattr(updated, "review_status", "pending_review"),
        review_notes=getattr(updated, "review_notes", None),
        candidates=cands,
    )


# ── Internal helpers ───────────────────────────────────────────────


def _get_entity(entity_type: EntityType, entity_id: int):
    if entity_type == "disease":
        return get_disease(entity_id)
    elif entity_type == "procedure":
        return get_procedure(entity_id)
    elif entity_type == "medication":
        return get_medication(entity_id)
    return None


def _update_entity(entity_type: EntityType, entity_id: int, updates: dict):
    if entity_type == "disease":
        return update_disease(entity_id, updates)
    elif entity_type == "procedure":
        return update_procedure(entity_id, updates)
    elif entity_type == "medication":
        return update_medication(entity_id, updates)
    return None


def _code_field(entity_type: EntityType) -> str:
    if entity_type == "disease":
        return "icd10_code"
    elif entity_type == "procedure":
        return "cpt_code"
    return "cui"  # medications use CUI as their primary code


def _update_join_row(entity_type: EntityType, link_id: int, updates: dict):
    if entity_type == "disease":
        return update_report_disease_fields(link_id, updates)
    elif entity_type == "procedure":
        return update_report_procedure_fields(link_id, updates)
    elif entity_type == "medication":
        return update_report_medication_fields(link_id, updates)
    return None


def _entity_id_from_link(entity_type: EntityType, link) -> int | None:
    if entity_type == "disease":
        return getattr(link, "disease_id", None)
    elif entity_type == "procedure":
        return getattr(link, "procedure_id", None)
    elif entity_type == "medication":
        return getattr(link, "medication_id", None)
    return None


def _get_entity_code(entity_type: EntityType, entity) -> str | None:
    if entity_type == "disease":
        return getattr(entity, "icd10_code", None)
    elif entity_type == "procedure":
        return getattr(entity, "cpt_code", None)
    return getattr(entity, "cui", None)


def _parse_candidates(json_str: str | None) -> list[dict] | None:
    if not json_str:
        return None
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return None
