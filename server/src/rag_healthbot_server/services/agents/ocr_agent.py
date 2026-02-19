from .common.contracts import IAgentInput, IAgentOutput
from pydantic import BaseModel


class IInputData(BaseModel):
    file_name: str
    file_content: bytes
    mime_type: str


class IOutputData(BaseModel):
    extracted_text: str


class IOCRAgentInput(IAgentInput):
    input: IInputData


class IOCRAgentOutput(IAgentOutput):
    output: IOutputData
