from __future__ import annotations

import json
import logging

import coloredlogs
from pydantic import BaseModel

from .common.contracts import IAgentInput, IAgentOutput
from rag_healthbot_server.services.db.ReportRepo import get_report
from rag_healthbot_server.services.db.MedicationRepo import update_medication
from rag_healthbot_server.services.db.DiseaseRepo import update_disease
from rag_healthbot_server.services.db.ProcedureRepo import update_procedure
from rag_healthbot_server.services.db.ReportMedicationRepo import (
    update_report_medication_fields,
)
from rag_healthbot_server.services.db.ReportDiseaseRepo import (
    update_report_disease_fields,
)
from rag_healthbot_server.services.db.ReportProcedureRepo import (
    update_report_procedure_fields,
)
from rag_healthbot_server.utilities.umls_coding import (
    resolve_disease_codes,
    resolve_medication_cui,
    resolve_procedure_codes,
)


logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", logger=logger)
logging.basicConfig(level=logging.DEBUG)
AGENT = "report_coding_agent"


class IInputData(BaseModel):
    report_id: int


class IOutputData(BaseModel):
    report_id: int
    medications_updated: int
    diseases_updated: int
    procedures_updated: int


class IReportCodingAgentInput(IAgentInput):
    input: IInputData


class IReportCodingAgentOutput(IAgentOutput):
    output: IOutputData | None = None


def run_report_coding_agent(
    payload: IReportCodingAgentInput,
) -> IReportCodingAgentOutput:
    """Background coding pass for one report.

    Resolves/updates CUI + ICD-10 + CPT + confidence/review status after the
    report has already been saved and returned to the UI.
    """
    report_id = payload.input.report_id
    logger.info("Running report coding agent for report_id=%s", report_id)

    report = get_report(report_id)
    if report is None:
        logger.error("Report not found for coding: report_id=%s", report_id)
        return IReportCodingAgentOutput(
            rund_id=payload.rund_id,
            status="failed",
            reason_code="invalid_input",
            output=None,
        )

    medications_updated = 0
    diseases_updated = 0
    procedures_updated = 0

    try:
        for link in report.medications or []:
            med = link.medication
            if med is None:
                continue

            if bool(getattr(med, "is_drug_class", False)):
                # Drug classes cannot be UMLS-coded; mark join row as needing review
                update_report_medication_fields(
                    link.id,
                    {"coding_confidence": 0.5, "review_status": "pending_review"},
                )
                medications_updated += 1
                continue

            if med.cui:
                # Already resolved globally; mark this occurrence as accepted
                update_report_medication_fields(
                    link.id,
                    {"coding_confidence": 1.0, "review_status": "accepted"},
                )
                continue

            resolution = resolve_medication_cui(med.name)
            if not resolution.cui:
                update_report_medication_fields(
                    link.id,
                    {"coding_confidence": 0.0, "review_status": "pending_review"},
                )
                continue

            # Write canonical code to entity row (shared across all reports)
            update_medication(med.id, {"cui": resolution.cui})
            # Write review state to join row (scoped to this report)
            update_report_medication_fields(
                link.id,
                {
                    "coding_confidence": resolution.confidence,
                    "review_status": resolution.review_status,
                },
            )
            medications_updated += 1

        for link in report.diseases or []:
            disease = link.disease
            if disease is None:
                continue

            if disease.cui and disease.icd10_code:
                # Already resolved globally; mark this occurrence as accepted
                update_report_disease_fields(
                    link.id,
                    {"coding_confidence": 1.0, "review_status": "accepted"},
                )
                continue

            resolution = resolve_disease_codes(disease.name)
            if not resolution.cui and not resolution.code:
                update_report_disease_fields(
                    link.id,
                    {"coding_confidence": 0.0, "review_status": "pending_review"},
                )
                continue

            # Write canonical codes to entity row
            canonical_updates: dict[str, str | float | None] = {}
            if resolution.cui:
                canonical_updates["cui"] = resolution.cui
            if resolution.code:
                canonical_updates["icd10_code"] = resolution.code
            if canonical_updates:
                update_disease(disease.id, canonical_updates)

            # Write review state to join row
            join_updates: dict[str, str | float | None] = {
                "coding_confidence": resolution.confidence,
                "review_status": resolution.review_status,
            }
            if resolution.candidates:
                join_updates["candidates_json"] = json.dumps(
                    resolution.candidates_as_dicts()
                )
            update_report_disease_fields(link.id, join_updates)
            diseases_updated += 1

        for link in report.procedures or []:
            procedure = link.procedure
            if procedure is None:
                continue

            if procedure.cui and procedure.cpt_code:
                # Already resolved globally; mark this occurrence as accepted
                update_report_procedure_fields(
                    link.id,
                    {"coding_confidence": 1.0, "review_status": "accepted"},
                )
                continue

            resolution = resolve_procedure_codes(procedure.name)
            if not resolution.cui and not resolution.code:
                update_report_procedure_fields(
                    link.id,
                    {"coding_confidence": 0.0, "review_status": "pending_review"},
                )
                continue

            # Write canonical codes to entity row
            canonical_updates = {}
            if resolution.cui:
                canonical_updates["cui"] = resolution.cui
            if resolution.code:
                canonical_updates["cpt_code"] = resolution.code
            if canonical_updates:
                update_procedure(procedure.id, canonical_updates)

            # Write review state to join row
            join_updates = {
                "coding_confidence": resolution.confidence,
                "review_status": resolution.review_status,
            }
            if resolution.candidates:
                join_updates["candidates_json"] = json.dumps(
                    resolution.candidates_as_dicts()
                )
            update_report_procedure_fields(link.id, join_updates)
            procedures_updated += 1

        logger.info(
            "Report coding complete for report_id=%s (medications=%d, diseases=%d, procedures=%d)",
            report_id,
            medications_updated,
            diseases_updated,
            procedures_updated,
        )
        return IReportCodingAgentOutput(
            rund_id=payload.rund_id,
            status="completed",
            output=IOutputData(
                report_id=report_id,
                medications_updated=medications_updated,
                diseases_updated=diseases_updated,
                procedures_updated=procedures_updated,
            ),
        )
    except Exception as exc:
        logger.exception("Report coding failed for report_id=%s: %s", report_id, exc)
        return IReportCodingAgentOutput(
            rund_id=payload.rund_id,
            status="failed",
            reason_code="processing_error",
            output=None,
        )
