from .common.contracts import IAgentInput, IAgentOutput
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain.messages import HumanMessage, SystemMessage
import logging, coloredlogs
from rag_healthbot_server.config import settings
import base64
import binascii
import io

from pypdf import PdfReader

logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", logger=logger)
logging.basicConfig(level=logging.DEBUG)
AGENT = "ocr_agent"


class IInputData(BaseModel):
    file_name: str
    file_content: str  ## As Base 64 encoded string
    mime_type: str


class IOutputData(BaseModel):
    extracted_text: str


class IOCRAgentInput(IAgentInput):
    input: IInputData


class IOCRAgentOutput(IAgentOutput):
    output: IOutputData | None = None


def _make_llm():
    llm = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_ocr_model,
        temperature=0.2,
        timeout=30,
    )
    return llm


def prepare_content(data_uri: str) -> list[SystemMessage | HumanMessage]:
    system = SystemMessage(
        content="You are an OCR agent that extracts text from medical documents. You receive a file and return the extracted text. Only return the extracted text without any additional commentary or formatting."
    )
    human = HumanMessage(
        content=[
            {
                "type": "text",
                "text": "Extract all readable text from this image and return only the extracted text. No explanation.",
            },
            {"type": "image_url", "image_url": {"url": data_uri}},
        ]
    )

    return [
        system,
        human,
    ]


def _decode_base64_payload(file_content: str) -> bytes:
    try:
        return base64.b64decode(file_content, validate=True)
    except (binascii.Error, ValueError) as e:
        raise ValueError("Invalid base64 payload") from e


def _extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages_text: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages_text.append(page_text)
    return "\n\n".join(pages_text).strip()


def run_ocr_agent(payload: IOCRAgentInput) -> IOCRAgentOutput:
    # Placeholder implementation for OCR processing
    file_name = payload.input.file_name
    file_content = payload.input.file_content
    mime_type = payload.input.mime_type

    logger.info(
        f"Running OCR agent for file: {payload.input.file_name} with MIME type: {payload.input.mime_type}"
    )

    # PDFs are not valid image payloads for Groq vision-style input.
    # For PDFs, extract embedded text locally.
    if mime_type == "application/pdf":
        try:
            pdf_bytes = _decode_base64_payload(file_content)
            extracted_text = _extract_text_from_pdf_bytes(pdf_bytes)
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {file_name}: {e}")
            return IOCRAgentOutput(
                rund_id=payload.rund_id,
                status="failed",
                reason_code="processing_error",
                output=None,
            )

        if not extracted_text:
            logger.error(
                f"PDF {file_name} contains no extractable text (likely scanned image PDF)"
            )
            return IOCRAgentOutput(
                rund_id=payload.rund_id,
                status="failed",
                reason_code="processing_error",
                output=None,
            )

        logger.info(
            f"PDF text extraction completed for {file_name}. Extracted text length: {len(extracted_text)}"
        )
        return IOCRAgentOutput(
            rund_id=payload.rund_id,
            status="completed",
            output=IOutputData(extracted_text=extracted_text),
        )

    # For images, use Groq multimodal (vision-style) message blocks.
    if not mime_type.startswith("image/"):
        logger.error(f"Unsupported MIME type for OCR: {mime_type}")
        return IOCRAgentOutput(
            rund_id=payload.rund_id,
            status="failed",
            reason_code="invalid_input",
            output=None,
        )

    data_uri = f"data:{mime_type};base64,{file_content}"
    llm = _make_llm()
    content = prepare_content(data_uri)

    try:
        logger.info(f"Invoking LLM for OCR extraction on file: {file_name}")
        response = llm.invoke(content)
        extracted_text = getattr(response, "content", None)

    except Exception as e:
        logger.error(f"Failed to extract text from file: {file_name}: {e}")
        return IOCRAgentOutput(
            rund_id=payload.rund_id,
            status="failed",
            reason_code="processing_error",
            output=None,
        )

    if not extracted_text:
        logger.error(f"OCR agent returned empty text for file: {file_name}")
        return IOCRAgentOutput(
            rund_id=payload.rund_id,
            status="failed",
            reason_code="processing_error",
            output=None,
        )

    logger.log(
        logging.INFO,
        f"OCR agent completed for file: {file_name}. Extracted text length: {len(extracted_text)}",
    )

    return IOCRAgentOutput(
        rund_id=payload.rund_id,
        status="completed",
        output=IOutputData(extracted_text=extracted_text),
    )
