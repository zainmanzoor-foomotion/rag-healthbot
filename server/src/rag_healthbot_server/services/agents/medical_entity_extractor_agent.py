from .common.contracts import IAgentInput, IAgentOutput
from pydantic import BaseModel


class MedicationEntity(BaseModel):
    text: str
    dosage: str | None = None
    frequency: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    purpose: str | None = None


class IInputData(BaseModel):
    text: str


class IOutputData(BaseModel):
    medications: list[MedicationEntity]


class IMedicalEntityExtractorAgentInput(IAgentInput):
    input: IInputData


class IMedicalEntityExtractorAgentOutput(IAgentOutput):
    output: IOutputData
