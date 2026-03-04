from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

from rag_healthbot_server.Models.Report import IReport
from rag_healthbot_server.Models.Medication import IMedication
from rag_healthbot_server.Models.Disease import IDisease
from rag_healthbot_server.Models.Procedure import IProcedure
from rag_healthbot_server.Models.ReportMedication import IReportMedication
from rag_healthbot_server.Models.ReportDisease import IReportDisease
from rag_healthbot_server.Models.ReportProcedure import IReportProcedure
from rag_healthbot_server.services.agents.common.entities import (
    MedicationEntity,
    DiseaseEntity,
    ProcedureEntity,
)

from rag_healthbot_server.services.db.ReportRepo import create_report
from rag_healthbot_server.services.db.MedicationRepo import (
    create_medication,
    get_medication_by_name,
    find_medications_name_startswith,
    rename_medication,
    update_medication,
)
from rag_healthbot_server.services.db.DiseaseRepo import (
    create_disease,
    get_disease_by_name,
    get_disease_by_cui,
    update_disease,
)
from rag_healthbot_server.services.db.ProcedureRepo import (
    create_procedure,
    get_procedure_by_name,
    get_procedure_by_cui,
    update_procedure,
)
from rag_healthbot_server.services.db.ReportMedicationRepo import (
    create_report_medication,
    get_medications_for_report,
)
from rag_healthbot_server.services.db.ReportDiseaseRepo import (
    create_report_disease,
    get_diseases_for_report,
)
from rag_healthbot_server.services.db.ReportProcedureRepo import (
    create_report_procedure,
    get_procedures_for_report,
)

from .medication_normalization import normalize_medication_name
from .report_dedup import find_existing_report
from .temporal_parsing import normalize_temporal_value, parse_reference_datetime


def save_report_entities_fast(
    *,
    file_name: str,
    extracted_text: str,
    summary: str,
    content_hash: str | None,
    extracted_text_hash: str | None,
    report_date: str | datetime | None = None,
    medications: list[MedicationEntity],
    diseases: list[DiseaseEntity] | None = None,
    procedures: list[ProcedureEntity] | None = None,
) -> int:
    """Fast-path persistence for report + entities (no UMLS/KB resolution).

    This keeps upload latency low by persisting extracted entities immediately.
    Expensive coding (UMLS/CPT/ICD10 resolution + confidence) is handled later
    by a background agent.
    """

    try:
        report = create_report(
            IReport(
                file_name=file_name,
                summary=summary,
                extracted_text=extracted_text,
                content_hash=content_hash,
                extracted_text_hash=extracted_text_hash,
            )
        )
    except IntegrityError:
        # The unique index on content_hash (non-NULL) or the new partial unique
        # index on extracted_text_hash fired — find and return the existing row.
        existing = find_existing_report(
            content_hash=content_hash,
            extracted_text_hash=extracted_text_hash,
        )
        if existing is not None:
            return existing.id
        raise

    report_id = report.id
    reference_datetime = parse_reference_datetime(report_date) or report.created_at

    # Idempotency guard: if entity links already exist this report was already
    # fully processed (e.g. a concurrent duplicate upload that slipped through).
    if (
        get_medications_for_report(report_id)
        or get_diseases_for_report(report_id)
        or get_procedures_for_report(report_id)
    ):
        return report_id

    # ── Persist medications (fast, no UMLS) ─────────────────────
    for med in medications:
        normalized_name = normalize_medication_name(med.name)
        if not normalized_name:
            continue

        cui = med.cui
        is_drug_class = getattr(med, "is_drug_class", False)

        if is_drug_class:
            confidence = 0.5
            review_status = "pending_review"
        else:
            confidence = None
            review_status = "pending_review"

        db_med = get_medication_by_name(normalized_name)
        if db_med is None:
            candidates = find_medications_name_startswith(normalized_name, limit=5)
            if len(candidates) == 1:
                try:
                    renamed = rename_medication(candidates[0].id, normalized_name)
                    if renamed is not None:
                        db_med = renamed
                except IntegrityError:
                    db_med = None

        if db_med is None:
            try:
                db_med = create_medication(
                    IMedication(
                        name=normalized_name,
                        cui=cui,
                        confidence=None,
                        review_status="pending_review",
                        is_drug_class=is_drug_class,
                    )
                )
            except IntegrityError:
                db_med = get_medication_by_name(normalized_name)
                if db_med is None:
                    raise
        elif cui and not db_med.cui:
            updates: dict[str, str | float | bool | None] = {"cui": cui}
            if is_drug_class and not getattr(db_med, "is_drug_class", False):
                updates["is_drug_class"] = True
            updated = update_medication(db_med.id, updates)
            if updated is not None:
                db_med = updated

        start_date = normalize_temporal_value(
            med.start_date,
            reference_datetime=reference_datetime,
        )
        end_date = normalize_temporal_value(
            med.end_date,
            reference_datetime=reference_datetime,
        )

        create_report_medication(
            IReportMedication(
                report_id=report_id,
                medication_id=db_med.id,
                dosage=med.dosage,
                frequency=med.frequency,
                start_date=start_date,
                end_date=end_date,
                purpose=med.purpose,
                coding_confidence=confidence,
                review_status="pending_review",
            )
        )
        if med.start_date and start_date is None:
            logger.warning(
                "Dropping unparseable medication.start_date=%r for report_id=%s",
                med.start_date,
                report_id,
            )
        if med.end_date and end_date is None:
            logger.warning(
                "Dropping unparseable medication.end_date=%r for report_id=%s",
                med.end_date,
                report_id,
            )

    # ── Persist diseases (fast, no coding) ──────────────────────
    for dis in diseases or []:
        name = (dis.name or "").strip()
        if not name:
            continue

        cui = dis.cui
        icd10_code = dis.icd10_code
        confidence = None
        review_status = "pending_review"
        candidates_json = None

        db_dis = None
        if cui:
            db_dis = get_disease_by_cui(cui)
        if db_dis is None:
            db_dis = get_disease_by_name(name)
        if db_dis is None:
            try:
                db_dis = create_disease(
                    IDisease(
                        name=name,
                        cui=cui,
                        icd10_code=icd10_code,
                        confidence=None,
                        review_status="pending_review",
                        candidates_json=None,
                    )
                )
            except IntegrityError:
                db_dis = get_disease_by_name(name)
                if db_dis is None:
                    raise
        elif not db_dis.cui or not db_dis.icd10_code:
            updates: dict[str, str | float | None] = {}
            if cui and not db_dis.cui:
                updates["cui"] = cui
            if icd10_code and not db_dis.icd10_code:
                updates["icd10_code"] = icd10_code
            if updates:
                updated = update_disease(db_dis.id, updates)
                if updated is not None:
                    db_dis = updated

        onset_date = normalize_temporal_value(
            dis.onset_date,
            reference_datetime=reference_datetime,
        )

        create_report_disease(
            IReportDisease(
                report_id=report_id,
                disease_id=db_dis.id,
                severity=dis.severity,
                status=dis.status,
                onset_date=onset_date,
                coding_confidence=None,
                review_status="pending_review",
            )
        )
        if dis.onset_date and onset_date is None:
            logger.warning(
                "Dropping unparseable disease.onset_date=%r for report_id=%s",
                dis.onset_date,
                report_id,
            )

    # ── Persist procedures (fast, no coding) ────────────────────
    for proc in procedures or []:
        name = (proc.name or "").strip()
        if not name:
            continue

        cui = proc.cui
        cpt_code = proc.cpt_code
        confidence = None
        review_status = "pending_review"
        candidates_json = None

        db_proc = None
        if cui:
            db_proc = get_procedure_by_cui(cui)
        if db_proc is None:
            db_proc = get_procedure_by_name(name)
        if db_proc is None:
            try:
                db_proc = create_procedure(
                    IProcedure(
                        name=name,
                        cui=cui,
                        cpt_code=cpt_code,
                        confidence=None,
                        review_status="pending_review",
                        candidates_json=None,
                    )
                )
            except IntegrityError:
                db_proc = get_procedure_by_name(name)
                if db_proc is None:
                    raise
        elif not db_proc.cui or not db_proc.cpt_code:
            updates: dict[str, str | float | None] = {}
            if cui and not db_proc.cui:
                updates["cui"] = cui
            if cpt_code and not db_proc.cpt_code:
                updates["cpt_code"] = cpt_code
            if updates:
                updated = update_procedure(db_proc.id, updates)
                if updated is not None:
                    db_proc = updated

        date_performed = normalize_temporal_value(
            proc.date_performed,
            reference_datetime=reference_datetime,
        )

        create_report_procedure(
            IReportProcedure(
                report_id=report_id,
                procedure_id=db_proc.id,
                date_performed=date_performed,
                body_site=proc.body_site,
                outcome=proc.outcome,
                coding_confidence=None,
                review_status="pending_review",
            )
        )
        if proc.date_performed and date_performed is None:
            logger.warning(
                "Dropping unparseable procedure.date_performed=%r for report_id=%s",
                proc.date_performed,
                report_id,
            )

    return report_id


def save_report_and_medications(
    *,
    file_name: str,
    extracted_text: str,
    summary: str,
    content_hash: str | None,
    extracted_text_hash: str | None,
    report_date: str | datetime | None = None,
    medications: list[MedicationEntity],
    diseases: list[DiseaseEntity] | None = None,
    procedures: list[ProcedureEntity] | None = None,
) -> int:
    """Backward-compatible wrapper.

    Prefer :func:`save_report_entities_fast` for new code paths.
    """
    return save_report_entities_fast(
        file_name=file_name,
        extracted_text=extracted_text,
        summary=summary,
        content_hash=content_hash,
        extracted_text_hash=extracted_text_hash,
        report_date=report_date,
        medications=medications,
        diseases=diseases,
        procedures=procedures,
    )
