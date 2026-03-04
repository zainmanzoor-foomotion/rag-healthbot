"""One-time backfill utility for diseases, procedures and medications
that were persisted before the UMLS API key was configured.

Now uses the multi-layer pipeline, populating confidence + review_status.

Usage (from the project root)::

    python -m rag_healthbot_server.utilities.backfill_codes

Or call ``backfill_all()`` programmatically.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


def backfill_diseases(force: bool = False) -> dict[str, int]:
    """Resolve CUI + ICD-10 for every disease row that is missing either.

    If *force* is ``True``, re-resolve **all** diseases (overwriting
    existing codes).
    """
    from rag_healthbot_server.services.db.DiseaseRepo import (
        list_diseases,
        update_disease,
    )
    from .umls_coding import resolve_disease_codes

    updated = 0
    skipped = 0
    failed = 0

    for disease in list_diseases():
        if not force and disease.cui and disease.icd10_code:
            continue  # already fully coded

        resolution = resolve_disease_codes(disease.name)
        updates: dict[str, str | float | None] = {}
        if resolution.cui:
            updates["cui"] = resolution.cui
        if resolution.code:
            updates["icd10_code"] = resolution.code
        updates["confidence"] = resolution.confidence
        updates["review_status"] = resolution.review_status
        if resolution.candidates:
            updates["candidates_json"] = json.dumps(resolution.candidates_as_dicts())

        if not resolution.cui and not resolution.code:
            skipped += 1
            logger.debug("No UMLS match for disease '%s'", disease.name)
            continue

        try:
            result = update_disease(disease.id, updates)
            if result is not None:
                updated += 1
                logger.info(
                    "Backfilled disease '%s' → CUI=%s ICD10=%s (confidence=%.2f, status=%s)",
                    disease.name,
                    result.cui,
                    result.icd10_code,
                    resolution.confidence,
                    resolution.review_status,
                )
            else:
                failed += 1
        except Exception:
            failed += 1
            logger.exception("Failed to backfill disease '%s'", disease.name)

    return {"updated": updated, "skipped": skipped, "failed": failed}


def backfill_procedures(force: bool = False) -> dict[str, int]:
    """Resolve CUI + CPT for every procedure row that is missing either.

    If *force* is ``True``, re-resolve **all** procedures.
    """
    from rag_healthbot_server.services.db.ProcedureRepo import (
        list_procedures,
        update_procedure,
    )
    from .umls_coding import resolve_procedure_codes

    updated = 0
    skipped = 0
    failed = 0

    for procedure in list_procedures():
        if not force and procedure.cui and procedure.cpt_code:
            continue

        resolution = resolve_procedure_codes(procedure.name)
        updates: dict[str, str | float | None] = {}
        if resolution.cui:
            updates["cui"] = resolution.cui
        if resolution.code:
            updates["cpt_code"] = resolution.code
        updates["confidence"] = resolution.confidence
        updates["review_status"] = resolution.review_status
        if resolution.candidates:
            updates["candidates_json"] = json.dumps(resolution.candidates_as_dicts())

        if not resolution.cui and not resolution.code:
            skipped += 1
            logger.debug("No UMLS match for procedure '%s'", procedure.name)
            continue

        try:
            result = update_procedure(procedure.id, updates)
            if result is not None:
                updated += 1
                logger.info(
                    "Backfilled procedure '%s' → CUI=%s CPT=%s (confidence=%.2f, status=%s)",
                    procedure.name,
                    result.cui,
                    result.cpt_code,
                    resolution.confidence,
                    resolution.review_status,
                )
            else:
                failed += 1
        except Exception:
            failed += 1
            logger.exception("Failed to backfill procedure '%s'", procedure.name)

    return {"updated": updated, "skipped": skipped, "failed": failed}


def backfill_medications(force: bool = False) -> dict[str, int]:
    """Resolve CUI for every medication row that is missing one.

    If *force* is ``True``, re-resolve **all** medications.
    """
    from rag_healthbot_server.services.db.MedicationRepo import (
        list_medications,
        update_medication,
    )
    from .umls_coding import resolve_medication_cui

    updated = 0
    skipped = 0
    failed = 0

    for medication in list_medications():
        if not force and medication.cui:
            continue

        resolution = resolve_medication_cui(medication.name)
        if not resolution.cui:
            skipped += 1
            logger.debug("No UMLS match for medication '%s'", medication.name)
            continue

        updates: dict[str, str | float | None] = {
            "cui": resolution.cui,
            "confidence": resolution.confidence,
            "review_status": resolution.review_status,
        }

        try:
            result = update_medication(medication.id, updates)
            if result is not None:
                updated += 1
                logger.info(
                    "Backfilled medication '%s' → CUI=%s (confidence=%.2f, status=%s)",
                    medication.name,
                    result.cui,
                    resolution.confidence,
                    resolution.review_status,
                )
            else:
                failed += 1
        except Exception:
            failed += 1
            logger.exception("Failed to backfill medication '%s'", medication.name)

    return {"updated": updated, "skipped": skipped, "failed": failed}


def backfill_all(force: bool = False) -> dict[str, dict[str, int]]:
    """Run all three backfill passes and return a summary.

    If *force* is ``True``, re-resolve **every** record even if it
    already has codes.
    """
    results: dict[str, dict[str, int]] = {}
    for label, fn in [
        ("medications", backfill_medications),
        ("diseases", backfill_diseases),
        ("procedures", backfill_procedures),
    ]:
        logger.info("── Backfilling %s ──", label)
        results[label] = fn(force=force)
        logger.info("  %s: %s", label, results[label])
    return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

    from rag_healthbot_server.config import settings
    from rag_healthbot_server.utilities.icd10_lookup import set_icd10_file
    from rag_healthbot_server.utilities.cpt_lookup import set_cpt_file

    if settings.icd10_file:
        set_icd10_file(settings.icd10_file)
    if settings.cpt_file:
        set_cpt_file(settings.cpt_file)

    backfill_all()
