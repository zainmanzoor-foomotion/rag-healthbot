from __future__ import annotations

import re
from string import capwords

from rag_healthbot_server.services.agents.common.entities import MedicationEntity


_FREQ_PATTERNS = (
    r"\bonce\s+daily\b",
    r"\btwice\s+daily\b",
    r"\bthree\s+times\s+daily\b",
    r"\bdaily\b",
    r"\bbid\b",
    r"\btid\b",
    r"\bqid\b",
    r"\bq\d+\s*h\b",
    r"\bevery\s+\d+\s*(hours?|days?|weeks?)\b",
)


def normalize_medication_name(raw_name: str) -> str:
    """Normalize an extracted medication string down to a stable drug name.

    Examples:
    - "Losartan 50 mg once daily (Lifelong)" -> "Losartan"
    - "sodium bicarbonate treatment" -> "Sodium Bicarbonate"

    This is intentionally heuristic, but should be stable/deterministic.
    """

    name = (raw_name or "").strip()
    if not name:
        return ""

    # Drop parenthetical notes.
    name = re.sub(r"\([^)]*\)", " ", name)

    # Remove common dosage/strength fragments (keep digits that are part of names like D3/B12).
    name = re.sub(
        r"\b\d+(?:\.\d+)?\s*(?:mg|g|mcg|µg|ug|ml|mL|iu|IU|units?|meq|%)\b",
        " ",
        name,
        flags=re.IGNORECASE,
    )

    # Remove routes/forms.
    name = re.sub(
        r"\b(?:tablet|tablets|tab|capsule|capsules|cap|injection|solution|suspension|cream|ointment|patch|spray|drops?)\b",
        " ",
        name,
        flags=re.IGNORECASE,
    )
    name = re.sub(
        r"\b(?:oral|po|iv|im|subcutaneous|sq|sc|topical|inh(?:aled)?|nasal)\b",
        " ",
        name,
        flags=re.IGNORECASE,
    )

    # Remove frequency phrasing.
    for pattern in _FREQ_PATTERNS:
        name = re.sub(pattern, " ", name, flags=re.IGNORECASE)

    # Remove helper words that cause near-duplicates.
    name = re.sub(
        r"\b(?:treatment|therapy|medication)\b", " ", name, flags=re.IGNORECASE
    )

    # Clean up punctuation/whitespace.
    name = re.sub(r"[^0-9A-Za-z\s/\-]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    if not name:
        return (raw_name or "").strip()

    return capwords(name)


def normalize_and_dedupe_medications(
    meds: list[MedicationEntity],
) -> list[MedicationEntity]:
    """Normalize med.name and collapse duplicates.

    Dedupe key is normalized name (case-insensitive). If multiple entries collapse,
    keeps whichever non-null detail fields are present.
    """

    by_key: dict[str, MedicationEntity] = {}
    for med in meds:
        normalized_name = normalize_medication_name(med.name)
        key = normalized_name.strip().lower()
        if not key:
            continue

        if key not in by_key:
            by_key[key] = MedicationEntity(
                name=normalized_name,
                dosage=med.dosage,
                frequency=med.frequency,
                start_date=med.start_date,
                end_date=med.end_date,
                purpose=med.purpose,
            )
            continue

        existing = by_key[key]
        by_key[key] = MedicationEntity(
            name=existing.name,
            dosage=existing.dosage or med.dosage,
            frequency=existing.frequency or med.frequency,
            start_date=existing.start_date or med.start_date,
            end_date=existing.end_date or med.end_date,
            purpose=existing.purpose or med.purpose,
        )

    return list(by_key.values())
