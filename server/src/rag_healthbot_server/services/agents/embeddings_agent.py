from .common.contracts import IAgentInput, IAgentOutput
from pydantic import BaseModel


class IInputData(BaseModel):
    texts: list[str]


class IOutputData(BaseModel):
    embeddings: list[list[float]]


class IEmbeddingsAgentInput(IAgentInput):
    input: IInputData


class IEmbeddingsAgentOutput(IAgentOutput):
    output: IOutputData
