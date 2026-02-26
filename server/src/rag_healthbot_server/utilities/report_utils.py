from __future__ import annotations

from rag_healthbot_server.services.agents.common.entities import MedicationEntity

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
            )
        )

    return normalize_and_dedupe_medications(meds)
