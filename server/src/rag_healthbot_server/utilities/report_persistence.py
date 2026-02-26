from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from rag_healthbot_server.Models.Report import IReport
from rag_healthbot_server.Models.Medication import IMedication
from rag_healthbot_server.Models.ReportMedication import IReportMedication
from rag_healthbot_server.services.agents.common.entities import MedicationEntity

from rag_healthbot_server.services.db.ReportRepo import create_report
from rag_healthbot_server.services.db.MedicationRepo import (
    create_medication,
    get_medication_by_name,
    find_medications_name_startswith,
    rename_medication,
)
from rag_healthbot_server.services.db.ReportMedicationRepo import (
    create_report_medication,
)

from .medication_normalization import normalize_medication_name
from .report_dedup import find_existing_report


def save_report_and_medications(
    *,
    file_name: str,
    extracted_text: str,
    summary: str,
    content_hash: str | None,
    extracted_text_hash: str | None,
    medications: list[MedicationEntity],
) -> int:
    """Persist report + medications using the existing repo functions."""

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
        # Another worker may have inserted the same content_hash concurrently.
        if content_hash:
            existing = find_existing_report(
                content_hash=content_hash,
                extracted_text_hash=None,
            )
            if existing is not None:
                return existing.id
        raise

    report_id = report.id

    for med in medications:
        normalized_name = normalize_medication_name(med.name)
        if not normalized_name:
            continue

        db_med = get_medication_by_name(normalized_name)

        if db_med is None:
            # If we have an older, overly-verbose medication row like
            # "Losartan 50 mg once daily", rename it to the canonical form.
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
                db_med = create_medication(IMedication(name=normalized_name))
            except IntegrityError:
                db_med = get_medication_by_name(normalized_name)
                if db_med is None:
                    raise

        create_report_medication(
            IReportMedication(
                report_id=report_id,
                medication_id=db_med.id,
                dosage=med.dosage,
                frequency=med.frequency,
                start_date=med.start_date,
                end_date=med.end_date,
                purpose=med.purpose,
            )
        )

    return report_id
