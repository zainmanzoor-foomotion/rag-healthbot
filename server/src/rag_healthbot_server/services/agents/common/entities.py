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
