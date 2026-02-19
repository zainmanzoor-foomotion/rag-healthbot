from pydantic import BaseModel
from uuid import UUID
from enum import Enum


class AgentType(str, Enum):
    OCR = "ocr"
    SUMMARIZATION = "summarization"
    MEDICATION_EXTRACTION = "medication_extraction"
    REPORT_EMBEDDING = "report_embedding"


class Status(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ReasonCode(str, Enum):
    NONE = "none"
    INVALID_INPUT = "invalid_input"
    PROCESSING_ERROR = "processing_error"


class IAgentInput(BaseModel):
    rund_id: UUID
    agent_type: AgentType
    input: dict | None = None
    constraints: dict | None = None
    schema_version: str | None = None


class IAgentOutput(BaseModel):
    rund_id: UUID
    status: Status
    reason_code: ReasonCode = ReasonCode.NONE
    output: dict | None = None
    schema_version: str | None = None
