from __future__ import annotations

from pydantic import BaseModel, Field, AliasChoices
from pydantic.config import ConfigDict


class MedicationEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Accept both {name: ...} and legacy {text: ...}
    name: str = Field(validation_alias=AliasChoices("name", "text"))
    dosage: str | None = None
    frequency: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    purpose: str | None = None
    cui: str | None = None

    # True when the entity is a therapeutic drug *class* (e.g. "Analgesics",
    # "Antibiotics") that cannot be mapped to a specific drug code.
    is_drug_class: bool = False

    # NER metadata (populated by scispacy_ner_agent)
    ner_source: str | None = None  # e.g. "bc5cdr", "bionlp", "general"
    ner_label: str | None = None  # e.g. "CHEMICAL", "DISEASE"
    ner_confidence: float | None = None  # entity-level NER score


class DiseaseEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    cui: str | None = None
    icd10_code: str | None = None
    severity: str | None = None
    status: str | None = None  # e.g. "active", "resolved", "chronic"
    onset_date: str | None = None

    ner_source: str | None = None
    ner_label: str | None = None
    ner_confidence: float | None = None


class ProcedureEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    cui: str | None = None
    cpt_code: str | None = None
    date_performed: str | None = None
    body_site: str | None = None
    outcome: str | None = None

    ner_source: str | None = None
    ner_label: str | None = None
    ner_confidence: float | None = None


class MedicalEntities(BaseModel):
    """Wrapper holding all extracted entity types from a single document."""

    medications: list[MedicationEntity] = []
    diseases: list[DiseaseEntity] = []
    procedures: list[ProcedureEntity] = []
