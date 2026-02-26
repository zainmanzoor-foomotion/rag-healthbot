from rq import get_current_job, Queue
from rq.job import Job
from redis import Redis
from typing import cast
from pydantic import BaseModel
import logging
import time
import coloredlogs

from rag_healthbot_server.config import settings

from rag_healthbot_server.utilities.report_persistence import (
    save_report_and_medications,
)

from .ocr_agent import (
    run_ocr_agent,
    IOCRAgentInput,
    IInputData as IOcrInputData,
)
from .summarizer_agent import (
    run_summarizer_agent,
    ISummarizerAgentInput,
    IInputData as ISummarizerInputData,
)
from .medical_entity_extractor_agent import (
    run_medical_entity_extractor_agent,
    IMedicalEntityExtractorAgentInput,
    IInputData as IEntityInputData,
)
from .embeddings_agent import (
    IEmbeddingsAgentInput,
    IInputData as IEmbeddingsInputData,
)

from rag_healthbot_server.services.agents.common.entities import MedicationEntity
from rag_healthbot_server.utilities.hashing import (
    report_content_hash,
    extracted_text_hash,
)
from rag_healthbot_server.utilities.medication_normalization import (
    normalize_medication_name,
    normalize_and_dedupe_medications,
)
from rag_healthbot_server.utilities.report_utils import (
    report_to_medication_entities,
)
from rag_healthbot_server.utilities.report_dedup import find_existing_report

from rag_healthbot_server.services.agents.common.contracts import (
    IAgentInput,
    IAgentOutput,
    AgentType,
)


redis = Redis.from_url(settings.redis_url)
queue = Queue("default", connection=redis)

logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", logger=logger)
logging.basicConfig(level=logging.DEBUG)

AGENT = "summary_orchestrator"
LOCK_PREFIX = "lock:report"


class IInputData(BaseModel):
    file_content: str
    mime_type: str
    file_name: str


class IOutputData(BaseModel):
    report_id: int
    summary: str
    medications: list[MedicationEntity]


class ISummaryOrchestratorInput(IAgentInput):
    input: IInputData


class ISummaryOrchestratorOutput(IAgentOutput):
    output: IOutputData | None = None


def _lock_key(file_name: str) -> str:
    return f"{LOCK_PREFIX}:{file_name}"


def _maybe_return_duplicate_report(
    payload: ISummaryOrchestratorInput,
    job: Job,
    *,
    content_hash: str | None,
    extracted_text_hash_value: str | None,
) -> ISummaryOrchestratorOutput | None:
    existing = find_existing_report(
        content_hash=content_hash,
        extracted_text_hash=extracted_text_hash_value,
    )

    if existing is None:
        return None

    job.meta["stage"] = "duplicate:skipped"
    job.meta["existing_report_id"] = getattr(existing, "id", None)
    job.save_meta()

    return ISummaryOrchestratorOutput(
        rund_id=payload.rund_id,
        status="completed",
        output=IOutputData(
            report_id=existing.id,
            summary=existing.summary,
            medications=report_to_medication_entities(existing),
        ),
    )


def run_summary_orchestrator(
    payload: ISummaryOrchestratorInput,
) -> ISummaryOrchestratorOutput:
    """
    Pipeline:
      1. OCR agent        → extracted text
      2. Summarizer agent → summary         (parallel-safe, but sequential here)
      3. Entity extractor → medications
      4. DB persist
      5. Enqueue embeddings agent (async, fire-and-forget)
      6. Return {report_id, summary, medications}
    """
    job = cast(Job, get_current_job())
    start_time = time.time()

    file_content = payload.input.file_content
    mime_type = payload.input.mime_type
    file_name = payload.input.file_name

    content_hash = report_content_hash(file_content)

    # ── Distributed lock (prevent duplicate processing) ─────────
    lock_key = _lock_key(content_hash or file_name)
    got = redis.set(lock_key, job.get_id(), nx=True, ex=60 * 10)
    if not got:
        logger.info(f"Report processing already in progress for {file_name}")
        return ISummaryOrchestratorOutput(
            rund_id=payload.rund_id,
            status="failed",
            reason_code="processing_error",
            output=None,
        )

    # Fast-path: if we've already processed this exact file content, short-circuit.
    dupe = _maybe_return_duplicate_report(
        payload,
        job,
        content_hash=content_hash,
        extracted_text_hash_value=None,
    )
    if dupe is not None:
        return dupe

    try:
        job.meta["stage"] = "ocr:started"
        job.save_meta()

        ocr_result = run_ocr_agent(
            IOCRAgentInput(
                rund_id=payload.rund_id,
                agent_type=AgentType.OCR,
                input=IOcrInputData(
                    file_name=file_name,
                    file_content=file_content,
                    mime_type=mime_type,
                ),
            )
        )

        if ocr_result.status != "completed" or ocr_result.output is None:
            raise RuntimeError(f"OCR agent failed: {ocr_result.reason_code}")

        extracted_text = ocr_result.output.extracted_text
        logger.info(f"OCR completed — extracted {len(extracted_text)} chars")

        extracted_text_hash_value = extracted_text_hash(extracted_text)

        # Second fast-path: some older rows may not have content_hash but can be deduped by text.
        dupe = _maybe_return_duplicate_report(
            payload,
            job,
            content_hash=None,
            extracted_text_hash_value=extracted_text_hash_value,
        )
        if dupe is not None:
            return dupe

        job.meta["stage"] = "summarizer:started"
        job.save_meta()

        summary_result = run_summarizer_agent(
            ISummarizerAgentInput(
                rund_id=payload.rund_id,
                agent_type=AgentType.SUMMARIZATION,
                input=ISummarizerInputData(text=extracted_text),
            )
        )

        if summary_result.status != "completed" or summary_result.output is None:
            raise RuntimeError(f"Summarizer agent failed: {summary_result.reason_code}")

        summary = summary_result.output.summary
        logger.info(f"Summarizer completed — summary length {len(summary)}")

        job.meta["stage"] = "entity_extractor:started"
        job.save_meta()

        entity_result = run_medical_entity_extractor_agent(
            IMedicalEntityExtractorAgentInput(
                rund_id=payload.rund_id,
                agent_type=AgentType.MEDICATION_EXTRACTION,
                input=IEntityInputData(text=extracted_text),
            )
        )

        if entity_result.status != "completed" or entity_result.output is None:
            raise RuntimeError(
                f"Entity extractor agent failed: {entity_result.reason_code}"
            )

        medications = normalize_and_dedupe_medications(entity_result.output.medications)
        logger.info(
            f"Entity extractor completed — found {len(medications)} medications"
        )

        job.meta["stage"] = "db_persist:started"
        job.save_meta()

        report_id = save_report_and_medications(
            file_name=file_name,
            extracted_text=extracted_text,
            summary=summary,
            content_hash=content_hash,
            extracted_text_hash=extracted_text_hash_value,
            medications=medications,
        )

        logger.info(
            f"Persisted report id={report_id} with {len(medications)} medications"
        )

        job.meta["stage"] = "embeddings:enqueued"
        job.save_meta()

        queue.enqueue(
            "rag_healthbot_server.services.agents.embeddings_agent.run_embeddings_agent",
            IEmbeddingsAgentInput(
                rund_id=payload.rund_id,
                agent_type=AgentType.REPORT_EMBEDDING,
                input=IEmbeddingsInputData(
                    texts=[extracted_text],
                ),
                constraints={"report_id": report_id, "file_name": file_name},
            ),
            job_timeout=10 * 60,
        )

        logger.info(f"Enqueued embeddings job for report id={report_id}")

        job.meta["stage"] = "completed"
        job.save_meta()

        return ISummaryOrchestratorOutput(
            rund_id=payload.rund_id,
            status="completed",
            output=IOutputData(
                report_id=report_id,
                summary=summary,
                medications=medications,
            ),
        )

    except Exception as e:
        logger.error(f"Summary orchestrator failed for {file_name}: {e}")
        job.meta["stage"] = "failed"
        job.meta["error"] = str(e)
        job.save_meta()
        return ISummaryOrchestratorOutput(
            rund_id=payload.rund_id,
            status="failed",
            reason_code="processing_error",
            output=None,
        )

    finally:
        redis.delete(lock_key)
        elapsed = time.time() - start_time
        logger.info(f"Summary orchestrator finished in {elapsed:.2f}s for {file_name}")
