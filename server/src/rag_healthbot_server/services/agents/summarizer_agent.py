from .common.contracts import IAgentInput, IAgentOutput
from pydantic import BaseModel


class IInputData(BaseModel):
    text: str


class IOutputData(BaseModel):
    summary: str


class ISummarizerAgentInput(IAgentInput):
    input: IInputData


class ISummarizerAgentOutput(IAgentOutput):
    output: IOutputData
