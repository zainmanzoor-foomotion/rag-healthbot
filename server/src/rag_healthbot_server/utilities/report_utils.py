from __future__ import annotations

from rag_healthbot_server.services.agents.common.entities import (
    MedicationEntity,
    DiseaseEntity,
    ProcedureEntity,
    MedicalEntities,
)

from .medication_normalization import (
    normalize_medication_name,
    normalize_and_dedupe_medications,
)


def report_to_medication_entities(report: object) -> list[MedicationEntity]:
    """Convert ORM Report -> MedicationEntity list (normalized + deduped)."""

    meds: list[MedicationEntity] = []
    links = getattr(report, "medications", []) or []
    for link in links:
        medication = getattr(link, "medication", None)
        name = getattr(medication, "name", None)
        if not name:
            continue

        normalized_name = normalize_medication_name(name)
        if not normalized_name:
            continue

        start_date = getattr(link, "start_date", None)
        end_date = getattr(link, "end_date", None)

        meds.append(
            MedicationEntity(
                name=normalized_name,
                dosage=getattr(link, "dosage", None),
                frequency=getattr(link, "frequency", None),
                start_date=start_date.isoformat() if start_date else None,
                end_date=end_date.isoformat() if end_date else None,
                purpose=getattr(link, "purpose", None),
                cui=getattr(medication, "cui", None),
            )
        )

    return normalize_and_dedupe_medications(meds)


def report_to_disease_entities(report: object) -> list[DiseaseEntity]:
    """Convert ORM Report -> DiseaseEntity list."""
    diseases: list[DiseaseEntity] = []
    links = getattr(report, "diseases", []) or []
    for link in links:
        disease = getattr(link, "disease", None)
        name = getattr(disease, "name", None)
        if not name:
            continue

        onset_date = getattr(link, "onset_date", None)

        diseases.append(
            DiseaseEntity(
                name=name,
                cui=getattr(disease, "cui", None),
                icd10_code=getattr(disease, "icd10_code", None),
                severity=getattr(link, "severity", None),
                status=getattr(link, "status", None),
                onset_date=onset_date.isoformat() if onset_date else None,
            )
        )
    return diseases


def report_to_procedure_entities(report: object) -> list[ProcedureEntity]:
    """Convert ORM Report -> ProcedureEntity list."""
    procedures: list[ProcedureEntity] = []
    links = getattr(report, "procedures", []) or []
    for link in links:
        procedure = getattr(link, "procedure", None)
        name = getattr(procedure, "name", None)
        if not name:
            continue

        date_performed = getattr(link, "date_performed", None)

        procedures.append(
            ProcedureEntity(
                name=name,
                cui=getattr(procedure, "cui", None),
                cpt_code=getattr(procedure, "cpt_code", None),
                date_performed=date_performed.isoformat() if date_performed else None,
                body_site=getattr(link, "body_site", None),
                outcome=getattr(link, "outcome", None),
            )
        )
    return procedures


def report_to_medical_entities(report: object) -> MedicalEntities:
    """Convert ORM Report -> full MedicalEntities wrapper."""
    return MedicalEntities(
        medications=report_to_medication_entities(report),
        diseases=report_to_disease_entities(report),
        procedures=report_to_procedure_entities(report),
    )
