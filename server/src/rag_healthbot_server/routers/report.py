import uuid
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from redis import Redis
from rq import Queue
from rq.job import Job

from rag_healthbot_server.config import settings
from rag_healthbot_server.services.agents.common.contracts import AgentType
from rag_healthbot_server.services.agents.summary_orchestrator import (
    run_summary_orchestrator,
    ISummaryOrchestratorInput,
    IInputData as IOrchestratorInputData,
)
from rag_healthbot_server.services.db.ReportRepo import (
    list_reports,
    get_report,
)

logger = logging.getLogger(__name__)

redis = Redis.from_url(settings.redis_url)
queue = Queue("default", connection=redis)

router = APIRouter(prefix="/report", tags=["report"])


# ── Response schemas ────────────────────────────────────────────────


class JobEnqueued(BaseModel):
    job_id: str
    file_name: str


class UploadResponse(BaseModel):
    jobs: list[JobEnqueued]


class ReportUploadItem(BaseModel):
    file_name: str
    mime_type: str
    file_content: str  # base64 string
    report_date: str | None = None


class UploadRequest(BaseModel):
    files: list[ReportUploadItem]


class MedicationOut(BaseModel):
    id: int | None = None  # canonical medication entity id
    link_id: int | None = None  # report_medication join row id (review handle)
    text: str
    dosage: str | None = None
    frequency: str | None = None
    purpose: str | None = None
    cui: str | None = None
    confidence: float | None = None
    review_status: str = "pending_review"
    is_drug_class: bool = False


class DiseaseOut(BaseModel):
    id: int | None = None  # canonical disease entity id
    link_id: int | None = None  # report_disease join row id (review handle)
    name: str
    cui: str | None = None
    icd10_code: str | None = None
    severity: str | None = None
    status: str | None = None
    confidence: float | None = None
    review_status: str = "pending_review"


class ProcedureOut(BaseModel):
    id: int | None = None  # canonical procedure entity id
    link_id: int | None = None  # report_procedure join row id (review handle)
    name: str
    cui: str | None = None
    cpt_code: str | None = None
    date_performed: str | None = None
    body_site: str | None = None
    outcome: str | None = None
    confidence: float | None = None
    review_status: str = "pending_review"


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    stage: str | None = None
    result: dict | None = None
    error: str | None = None


class ReportOut(BaseModel):
    id: int
    file_name: str
    summary: str
    extracted_text: str | None = None
    medications: list[MedicationOut] = []
    diseases: list[DiseaseOut] = []
    procedures: list[ProcedureOut] = []

    class Config:
        from_attributes = True


# ── POST /api/report — upload files, enqueue jobs ──────────────────


@router.post("", response_model=UploadResponse)
async def upload_reports(payload: UploadRequest):
    """
    Accept one or more PDF uploads.
    Each file is enqueued as a separate RQ job running the summary orchestrator.
    Returns the job IDs so the client can poll for status.
    """
    if not payload.files:
        raise HTTPException(status_code=400, detail="No files provided")

    jobs: list[JobEnqueued] = []

    for file in payload.files:
        mime_type = file.mime_type
        file_name = file.file_name
        file_content = file.file_content
        report_date = file.report_date

        run_id = uuid.uuid4()

        payload = ISummaryOrchestratorInput(
            rund_id=run_id,
            agent_type=AgentType.SUMMARIZATION,
            input=IOrchestratorInputData(
                file_content=file_content,
                mime_type=mime_type,
                file_name=file_name,
                report_date=report_date,
            ),
        )

        rq_job = queue.enqueue(
            run_summary_orchestrator,
            payload,
            job_timeout=10 * 60,
        )

        logger.info(f"Enqueued summary job {rq_job.id} for {file_name}")
        jobs.append(JobEnqueued(job_id=rq_job.id, file_name=file_name))

    return UploadResponse(jobs=jobs)


# ── GET /api/report/jobs/{job_id} — poll job status ────────────────


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    """
    Poll the status of a previously enqueued summary job.
    Returns the stage, and the full result once completed.
    """
    try:
        job = Job.fetch(job_id, connection=redis)
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")

    status = job.get_status()
    meta = job.meta or {}

    response = JobStatusResponse(
        job_id=job_id,
        status=status,
        stage=meta.get("stage"),
    )

    if status == "finished" and job.result is not None:
        result = job.result
        # result is an ISummaryOrchestratorOutput — serialise it
        if hasattr(result, "model_dump"):
            response.result = result.model_dump()
        elif isinstance(result, dict):
            response.result = result

    if status == "failed":
        response.error = meta.get("error") or str(job.exc_info or "Unknown error")

    return response


# ── GET /api/report — list all reports ──────────────────────────────


@router.get("", response_model=list[ReportOut])
def get_reports():
    """Return all persisted reports (newest first)."""
    reports = list_reports()
    out = []
    for r in reports:
        meds = []
        for link in r.medications or []:
            med = link.medication
            meds.append(
                MedicationOut(
                    id=med.id if med else None,
                    link_id=link.id,
                    text=med.name if med else "Unknown",
                    dosage=link.dosage,
                    frequency=link.frequency,
                    purpose=link.purpose,
                    cui=getattr(med, "cui", None) if med else None,
                    confidence=getattr(link, "coding_confidence", None),
                    review_status=(getattr(link, "review_status", "pending_review")),
                    is_drug_class=(
                        bool(getattr(med, "is_drug_class", False)) if med else False
                    ),
                )
            )
        diseases = []
        for link in getattr(r, "diseases", []) or []:
            dis = link.disease
            diseases.append(
                DiseaseOut(
                    id=dis.id if dis else None,
                    link_id=link.id,
                    name=dis.name if dis else "Unknown",
                    cui=getattr(dis, "cui", None) if dis else None,
                    icd10_code=getattr(dis, "icd10_code", None) if dis else None,
                    severity=link.severity,
                    status=link.status,
                    confidence=getattr(link, "coding_confidence", None),
                    review_status=(getattr(link, "review_status", "pending_review")),
                )
            )
        procedures = []
        for link in getattr(r, "procedures", []) or []:
            proc = link.procedure
            date_performed = getattr(link, "date_performed", None)
            procedures.append(
                ProcedureOut(
                    id=proc.id if proc else None,
                    link_id=link.id,
                    name=proc.name if proc else "Unknown",
                    cui=getattr(proc, "cui", None) if proc else None,
                    cpt_code=getattr(proc, "cpt_code", None) if proc else None,
                    date_performed=(
                        date_performed.isoformat() if date_performed else None
                    ),
                    body_site=link.body_site,
                    outcome=link.outcome,
                    confidence=getattr(link, "coding_confidence", None),
                    review_status=(getattr(link, "review_status", "pending_review")),
                )
            )
        out.append(
            ReportOut(
                id=r.id,
                file_name=r.file_name,
                summary=r.summary,
                extracted_text=r.extracted_text,
                medications=meds,
                diseases=diseases,
                procedures=procedures,
            )
        )
    return out


# ── GET /api/report/{report_id} — single report ────────────────────


@router.get("/{report_id}", response_model=ReportOut)
def get_report_by_id(report_id: int):
    """Return a single report with its linked medications, diseases, procedures."""
    report = get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    meds = []
    for link in report.medications or []:
        med = link.medication
        meds.append(
            MedicationOut(
                id=med.id if med else None,
                link_id=link.id,
                text=med.name if med else "Unknown",
                dosage=link.dosage,
                frequency=link.frequency,
                purpose=link.purpose,
                cui=getattr(med, "cui", None) if med else None,
                confidence=getattr(link, "coding_confidence", None),
                review_status=(getattr(link, "review_status", "pending_review")),
                is_drug_class=(
                    bool(getattr(med, "is_drug_class", False)) if med else False
                ),
            )
        )

    diseases = []
    for link in getattr(report, "diseases", []) or []:
        dis = link.disease
        diseases.append(
            DiseaseOut(
                id=dis.id if dis else None,
                link_id=link.id,
                name=dis.name if dis else "Unknown",
                cui=getattr(dis, "cui", None) if dis else None,
                icd10_code=getattr(dis, "icd10_code", None) if dis else None,
                severity=link.severity,
                status=link.status,
                confidence=getattr(link, "coding_confidence", None),
                review_status=(getattr(link, "review_status", "pending_review")),
            )
        )

    procedures = []
    for link in getattr(report, "procedures", []) or []:
        proc = link.procedure
        date_performed = getattr(link, "date_performed", None)
        procedures.append(
            ProcedureOut(
                id=proc.id if proc else None,
                link_id=link.id,
                name=proc.name if proc else "Unknown",
                cui=getattr(proc, "cui", None) if proc else None,
                cpt_code=getattr(proc, "cpt_code", None) if proc else None,
                date_performed=date_performed.isoformat() if date_performed else None,
                body_site=link.body_site,
                outcome=link.outcome,
                confidence=getattr(link, "coding_confidence", None),
                review_status=(getattr(link, "review_status", "pending_review")),
            )
        )

    return ReportOut(
        id=report.id,
        file_name=report.file_name,
        summary=report.summary,
        extracted_text=report.extracted_text,
        medications=meds,
        diseases=diseases,
        procedures=procedures,
    )
