from .common.contracts import IAgentInput, IAgentOutput
from pydantic import BaseModel
from pydantic.config import ConfigDict
import logging, coloredlogs
from langchain.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_core.output_parsers import PydanticOutputParser
from rag_healthbot_server.config import settings
from rag_healthbot_server.services.agents.common.entities import MedicationEntity

logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", logger=logger)
logging.basicConfig(level=logging.DEBUG)
AGENT = "medical_entity_extractor_agent"


class IInputData(BaseModel):
    text: str


class IOutputData(BaseModel):
    model_config = ConfigDict(extra="ignore")
    medications: list[MedicationEntity]


class IMedicalEntityExtractorAgentInput(IAgentInput):
    input: IInputData


class IMedicalEntityExtractorAgentOutput(IAgentOutput):
    output: IOutputData | None = None


SYSTEM_PROMPT = """You are a medical entity extraction system.
You will be given the text of a medical document (lab report, prescription, discharge summary, etc.).

Your job:
1. Identify every medication mentioned in the text.
2. For each medication, extract:
        - name: the medication name ONLY (required)
    - dosage: strength and form (e.g. "500 mg tablet"), or null if not stated
    - frequency: how often it is taken (e.g. "twice daily"), or null if not stated
    - start_date: when it was started (ISO date or free text), or null if not stated
    - end_date: when it was stopped, or null if not stated
    - purpose: why it was prescribed, or null if not stated

Name rules (very important):
- `name` must NOT include dosage, frequency, route, duration, or notes.
    Example: "Losartan 50 mg once daily (lifelong)" -> name="Losartan", dosage="50 mg", frequency="once daily".
- If the text gives a brand+generic together, prefer the generic as `name` (put the brand in purpose if needed).
- If a document mentions a medication class/category (e.g. "analgesics", "antibiotics") without naming a specific drug,
    still include it as an entity using the class/category as `name`.

Rules:
- Only extract medications that are explicitly mentioned.
- Do NOT invent or infer medications that are not in the text.
- If a document mentions a medication class/category (e.g. "analgesics", "antibiotics", "steroids")
    without naming a specific drug, still include it as a medication entity using the exact mention in `name`.
- If no medications are found, return an empty list.
- Return ONLY valid JSON matching the schema, no commentary."""


def _prepare_messages(text: str) -> list[SystemMessage | HumanMessage]:
    parser = PydanticOutputParser(pydantic_object=IOutputData)
    format_instructions = parser.get_format_instructions()

    return [
        SystemMessage(content=f"{SYSTEM_PROMPT}\n\n{format_instructions}"),
        HumanMessage(
            content=(
                "Extract all medication entities from the following medical document. "
                "Return JSON only.\n\n"
                f"{text}"
            )
        ),
    ]


def _make_llm():
    llm = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.llm_model,
        temperature=0.0,
        timeout=30,
    )
    return llm


def run_medical_entity_extractor_agent(
    payload: IMedicalEntityExtractorAgentInput,
) -> IMedicalEntityExtractorAgentOutput:
    # Placeholder implementation for medical entity extraction
    text = payload.input.text

    logger.info(
        f"Running medical entity extractor agent with input text of length: {len(text)}"
    )

    llm = _make_llm()
    content = _prepare_messages(text)
    parser = PydanticOutputParser(pydantic_object=IOutputData)

    try:
        logger.info(
            f"Invoking LLM for medical entity extraction of text of length: {len(text)}"
        )
        response = llm.invoke(content)
        raw = getattr(response, "content", "") or ""
        result: IOutputData = parser.parse(raw)
        if not result.medications:
            logger.debug(
                "No medication entities extracted. Raw model output: %s",
                raw,
            )
        logger.info(f"Extracted {len(result.medications)} medication entities")

    except Exception as e:
        logger.error(f"Failed to extract medical entities from text: {e}")
        return IMedicalEntityExtractorAgentOutput(
            rund_id=payload.rund_id,
            status="failed",
            reason_code="processing_error",
            output=None,
        )

    logger.log(
        logging.INFO,
        f"Medical entity extractor agent completed for text of length: {len(text)}",
    )

    return IMedicalEntityExtractorAgentOutput(
        rund_id=payload.rund_id,
        status="completed",
        output=result,
    )
