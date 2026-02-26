from .common.contracts import IAgentInput, IAgentOutput
from langchain.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from rag_healthbot_server.config import settings
from pydantic import BaseModel
import logging, coloredlogs

logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", logger=logger)
logging.basicConfig(level=logging.DEBUG)
AGENT = "summarizer_agent"


class IInputData(BaseModel):
    text: str


class IOutputData(BaseModel):
    summary: str


class ISummarizerAgentInput(IAgentInput):
    input: IInputData


class ISummarizerAgentOutput(IAgentOutput):
    output: IOutputData


def prepare_content(text: str) -> list[SystemMessage | HumanMessage]:
    system = SystemMessage(
        content="You are a summarizer agent that summarizes medical documents. You receive a text and return a concise summary. Only return the summary without any additional commentary or formatting."
    )
    human = HumanMessage(
        content=[
            {
                "type": "text",
                "text": "Summarize the following medical document text concisely and only return the summary.",
            },
            {"type": "text", "text": text},
        ]
    )

    return [
        system,
        human,
    ]


def _make_llm():
    llm = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_ocr_model,
        temperature=0.2,
        timeout=30,
    )
    return llm


def run_summarizer_agent(payload: ISummarizerAgentInput) -> ISummarizerAgentOutput:
    text = payload.input.text

    logger.info(f"Running summarizer agent with input text of length: {len(text)}")

    llm = _make_llm()
    content = prepare_content(text)

    try:
        logger.info(f"Invoking LLM for summarization of text of length: {len(text)}")
        response = llm.invoke(content)
        summary = getattr(response, "content", None)

    except Exception as e:
        logger.error(f"Failed to summarize text: {e}")
        return ISummarizerAgentOutput(
            rund_id=payload.rund_id,
            status="failed",
            reason_code="processing_error",
            output=None,
        )

    logger.log(
        logging.INFO,
        f"Summarizer agent completed for text of length: {len(text)}",
    )

    return ISummarizerAgentOutput(
        rund_id=payload.rund_id, status="completed", output=IOutputData(summary=summary)
    )
