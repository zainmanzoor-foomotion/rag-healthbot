from __future__ import annotations

import json

from .common.contracts import IAgentInput, IAgentOutput, AgentType
from pydantic import BaseModel
from pydantic.config import ConfigDict
import logging, coloredlogs
from langchain.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from rag_healthbot_server.config import settings
from rag_healthbot_server.services.agents.common.entities import (
    MedicationEntity,
    DiseaseEntity,
    ProcedureEntity,
)
from rag_healthbot_server.services.agents.scispacy_ner_agent import (
    run_scispacy_ner_agent,
    IScispaCyNERAgentInput,
    IInputData as INERInputData,
    ClassifiedEntities,
    ClassifiedEntity,
)

logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", logger=logger)
logging.basicConfig(level=logging.DEBUG)
AGENT = "medical_entity_extractor_agent"


class IInputData(BaseModel):
    text: str


class IOutputData(BaseModel):
    model_config = ConfigDict(extra="ignore")
    medications: list[MedicationEntity]
    diseases: list[DiseaseEntity] = []
    procedures: list[ProcedureEntity] = []


class IMedicalEntityExtractorAgentInput(IAgentInput):
    input: IInputData


class IMedicalEntityExtractorAgentOutput(IAgentOutput):
    output: IOutputData | None = None


# ── Compact output schema (replaces verbose PydanticOutputParser) ──
_OUTPUT_EXAMPLE = {
    "medications": [
        {
            "name": "Losartan",
            "dosage": "50 mg",
            "frequency": "once daily",
            "start_date": None,
            "end_date": None,
            "purpose": "hypertension",
            "cui": None,
            "is_drug_class": False,
        },
        {
            "name": "Analgesics",
            "dosage": None,
            "frequency": None,
            "start_date": None,
            "end_date": None,
            "purpose": "pain relief",
            "cui": None,
            "is_drug_class": True,
        },
    ],
    "diseases": [
        {
            "name": "Hypertension",
            "cui": None,
            "icd10_code": None,
            "severity": "mild",
            "status": "active",
            "onset_date": None,
        }
    ],
    "procedures": [
        {
            "name": "Appendectomy",
            "cui": None,
            "cpt_code": None,
            "date_performed": "2019",
            "body_site": "abdomen",
            "outcome": "successful",
        }
    ],
}
_FORMAT_INSTRUCTIONS = f"Return ONLY valid JSON (no markdown, no commentary) matching this structure:\n{json.dumps(_OUTPUT_EXAMPLE, indent=2)}"

# ~1200 chars vs ~2800 before
SYSTEM_PROMPT = """You are a medical entity extraction system. Given a medical document and optional NER-detected entity lists, extract and enrich entities.

NER lists (if provided):
- Medications (high confidence) — enrich with dosage, frequency, dates, purpose from the text.
- Diseases (high confidence) — enrich with severity, status, onset_date.
- Procedure candidates (need confirmation) — include only real medical procedures; discard anatomy terms used descriptively. Enrich with date_performed, body_site, outcome.

Rules:
- Add entities the NER missed. Do NOT invent entities absent from the text.
- Medication `name` must NOT include dosage/frequency/route. Prefer generic over brand names.
- If a medication is a therapeutic drug *class* (e.g. \"Analgesics\", \"Antibiotics\", \"Statins\"), set `is_drug_class` to true. Keep these — they are clinically important.
- Set fields to null when not stated in the text. Set cui, icd10_code, cpt_code to null.
- Empty categories → empty list []."""


# ── Text budget ────────────────────────────────────────────────────
# Each chunk must fit comfortably inside the model context window.
# System + format instructions ≈ 600 tokens, NER hints ≈ 200 tokens,
# leaving ~4 200 tokens (~17 000 chars) for the document chunk itself.
# Output is uncapped (None) — the model may emit as many entities as the
# chunk contains without risk of mid-JSON truncation.  The input side is
# already bounded by _CHUNK_SIZE_CHARS so context overflow is impossible.
_CHUNK_SIZE_CHARS = 17_000  # document text per LLM call
_CHUNK_OVERLAP_CHARS = 500  # overlap to catch entities near chunk boundaries
_MAX_TOKENS_RESPONSE: int | None = None  # no cap — emit all entities


def _split_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split *text* into overlapping chunks of at most *chunk_size* chars.

    Each chunk (except the first) starts *overlap* chars before the end of
    the previous chunk so entities straddling a boundary are not missed.
    Chunks are cut at the last newline within the chunk to avoid splitting
    mid-sentence when possible.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            # Prefer cutting at a newline so we don't split mid-sentence
            nl = text.rfind("\n", start + chunk_size // 2, end)
            if nl != -1:
                end = nl + 1
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def _prepare_messages(
    text: str,
    classified: ClassifiedEntities | None = None,
    raw_entity_names: list[str] | None = None,
    chunk_label: str | None = None,
) -> list[SystemMessage | HumanMessage]:
    ner_context = ""

    if classified and (
        classified.medications or classified.diseases or classified.procedure_candidates
    ):
        sections: list[str] = []
        if classified.medications:
            sections.append("Medications: " + ", ".join(classified.medication_names()))
        if classified.diseases:
            sections.append("Diseases: " + ", ".join(classified.disease_names()))
        if classified.procedure_candidates:
            sections.append(
                "Procedure candidates: "
                + ", ".join(classified.procedure_candidate_names())
            )
        ner_context = "\nNER entities:\n" + "\n".join(sections) + "\n"
    elif raw_entity_names:
        ner_context = (
            "\nNER entities (unclassified): " + ", ".join(raw_entity_names) + "\n"
        )

    label = f" [{chunk_label}]" if chunk_label else ""

    return [
        SystemMessage(content=f"{SYSTEM_PROMPT}\n\n{_FORMAT_INSTRUCTIONS}"),
        HumanMessage(content=(f"{ner_context}\nDocument text{label}:\n{text}")),
    ]


def _merge_outputs(results: list[IOutputData]) -> IOutputData:
    """Merge entity lists from multiple chunks, deduplicating by name.

    When the same entity name appears in more than one chunk, the version
    with more non-null fields is kept (richer context wins).
    """

    def _richness(obj: BaseModel) -> int:
        return sum(1 for v in obj.model_dump().values() if v is not None)

    seen_meds: dict[str, MedicationEntity] = {}
    seen_diseases: dict[str, DiseaseEntity] = {}
    seen_procs: dict[str, ProcedureEntity] = {}

    for res in results:
        for med in res.medications:
            key = med.name.strip().lower()
            if key not in seen_meds or _richness(med) > _richness(seen_meds[key]):
                seen_meds[key] = med
        for dis in res.diseases:
            key = dis.name.strip().lower()
            if key not in seen_diseases or _richness(dis) > _richness(
                seen_diseases[key]
            ):
                seen_diseases[key] = dis
        for proc in res.procedures:
            key = proc.name.strip().lower()
            if key not in seen_procs or _richness(proc) > _richness(seen_procs[key]):
                seen_procs[key] = proc

    return IOutputData(
        medications=list(seen_meds.values()),
        diseases=list(seen_diseases.values()),
        procedures=list(seen_procs.values()),
    )


def _make_llm():
    llm = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.llm_model,
        temperature=0.0,
        timeout=30,
        max_tokens=_MAX_TOKENS_RESPONSE,
    )
    return llm


def _repair_truncated_json(raw: str) -> str | None:
    """Attempt to repair a JSON object truncated at the token limit.

    Two-pass strategy:
    1. Close any open string literal and close all open brackets.
       Returns immediately if this produces valid JSON.
    2. If pass 1 fails (e.g. bare key with no value, or partial number),
       backtrack to the last comma at the current stack depth, strip
       everything from that comma onward, then close the brackets.
       This drops the incomplete last element cleanly.

    Returns the repaired string, or ``None`` if neither pass succeeds.
    """
    if not raw.strip():
        return None

    stack: list[str] = []  # unmatched '{' and '['
    in_string = False
    escape_next = False
    # Map nesting_depth -> index of the last ',' seen at that depth
    last_comma_at: dict[int, int] = {}

    for i, ch in enumerate(raw):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        depth = len(stack)
        if ch == ",":
            last_comma_at[depth] = i
        elif ch in ("{", "["):
            stack.append(ch)
        elif ch == "}" and stack and stack[-1] == "{":
            stack.pop()
            # comma records inside the closed scope are no longer relevant
            last_comma_at.pop(len(stack) + 1, None)
        elif ch == "]" and stack and stack[-1] == "[":
            stack.pop()
            last_comma_at.pop(len(stack) + 1, None)

    def _close(s: list[str]) -> str:
        return "".join("}" if c == "{" else "]" for c in reversed(s))

    # ── Pass 1: close open string + close brackets ────────────────
    suffix1 = ('"' if in_string else "") + _close(stack)
    candidate1 = raw + suffix1
    try:
        json.loads(candidate1)
        return candidate1
    except json.JSONDecodeError:
        pass

    # ── Pass 2: backtrack to last safe comma at current depth ─────
    depth = len(stack)
    comma_pos = last_comma_at.get(depth)
    if comma_pos is not None:
        truncated = raw[:comma_pos]  # drop the comma and everything after it
        candidate2 = truncated + _close(stack)
        try:
            json.loads(candidate2)
            return candidate2
        except json.JSONDecodeError:
            pass

    return None


def _build_ner_lookup(entities: list[ClassifiedEntity]) -> dict[str, ClassifiedEntity]:
    """Build a case-insensitive name → ClassifiedEntity lookup."""
    return {e.name.lower(): e for e in entities}


def _propagate_ner_metadata(
    result: IOutputData, classified: ClassifiedEntities
) -> None:
    """Copy NER source/label/confidence onto the LLM-enriched entities.

    Entities kept from the NER pass get their original metadata.
    Entities added by the LLM (not in NER) are tagged with ner_source="llm".
    """
    med_lookup = _build_ner_lookup(classified.medications)
    dis_lookup = _build_ner_lookup(classified.diseases)
    proc_lookup = _build_ner_lookup(classified.procedure_candidates)

    for med in result.medications:
        ner = med_lookup.get(med.name.lower())
        if ner:
            med.ner_source = ner.source_model
            med.ner_label = ner.source_label
            med.ner_confidence = ner.ner_confidence
            # Entities coming from the drug-class lexicon are always classes
            if ner.source_label == "DRUG_CLASS":
                med.is_drug_class = True
        else:
            med.ner_source = "llm"
            med.ner_confidence = 0.6  # LLM-added entities get lower NER score

    for dis in result.diseases:
        ner = dis_lookup.get(dis.name.lower())
        if ner:
            dis.ner_source = ner.source_model
            dis.ner_label = ner.source_label
            dis.ner_confidence = ner.ner_confidence
        else:
            dis.ner_source = "llm"
            dis.ner_confidence = 0.6

    for proc in result.procedures:
        ner = proc_lookup.get(proc.name.lower())
        if ner:
            proc.ner_source = ner.source_model
            proc.ner_label = ner.source_label
            proc.ner_confidence = ner.ner_confidence
        else:
            proc.ner_source = "llm"
            proc.ner_confidence = 0.5  # LLM-added procedures lower still


def run_medical_entity_extractor_agent(
    payload: IMedicalEntityExtractorAgentInput,
) -> IMedicalEntityExtractorAgentOutput:
    """Hybrid extraction: scispaCy NER (pre-classified) → LLM enrichment."""
    text = payload.input.text

    logger.info(
        "Running hybrid medical entity extractor on text of length: %d", len(text)
    )

    # ── Step 1: scispaCy NER (pre-classified entities) ──────────
    classified: ClassifiedEntities | None = None
    raw_entity_names: list[str] | None = None
    try:
        ner_result = run_scispacy_ner_agent(
            IScispaCyNERAgentInput(
                rund_id=payload.rund_id,
                agent_type=AgentType.MEDICAL_NER,
                input=INERInputData(text=text),
            )
        )
        if ner_result.status == "completed" and ner_result.output is not None:
            classified = ner_result.output.classified_entities
            raw_entity_names = ner_result.output.raw_entity_names
            logger.info(
                "NER pre-pass: %d medications, %d diseases, %d procedure candidates",
                len(classified.medications),
                len(classified.diseases),
                len(classified.procedure_candidates),
            )
        else:
            logger.warning("NER pre-pass failed — falling back to LLM-only extraction")
    except Exception as e:
        logger.warning("NER pre-pass error: %s — falling back to LLM-only", e)

    # ── Step 2: LLM classification + enrichment (chunked) ───────────
    llm = _make_llm()
    chunks = _split_chunks(text, _CHUNK_SIZE_CHARS, _CHUNK_OVERLAP_CHARS)
    total_chunks = len(chunks)
    logger.info("Processing %d chunk(s) for entity extraction", total_chunks)

    chunk_results: list[IOutputData] = []

    for chunk_idx, chunk_text in enumerate(chunks, start=1):
        chunk_label = f"chunk {chunk_idx}/{total_chunks}" if total_chunks > 1 else None
        messages = _prepare_messages(
            chunk_text, classified, raw_entity_names, chunk_label=chunk_label
        )

        chunk_result: IOutputData | None = None

        # Up to 2 attempts per chunk (second call may produce a
        # differently-truncated response that the repair can handle).
        for attempt in range(1, 3):
            try:
                logger.info(
                    "LLM call chunk %d/%d attempt %d (text_len=%d)",
                    chunk_idx,
                    total_chunks,
                    attempt,
                    len(chunk_text),
                )
                response = llm.invoke(messages)
                raw = getattr(response, "content", "") or ""

                # Strip markdown fences
                cleaned = raw.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[-1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[: cleaned.rfind("```")]
                cleaned = cleaned.strip()

                # ── Primary parse ──────────────────────────────
                try:
                    chunk_result = IOutputData.model_validate_json(cleaned)
                    break  # success — stop retrying this chunk
                except Exception as parse_err:
                    logger.warning(
                        "JSON parse failed (chunk %d, attempt %d): %s — trying repair",
                        chunk_idx,
                        attempt,
                        parse_err,
                    )
                    repaired = _repair_truncated_json(cleaned)
                    if repaired is None:
                        logger.warning(
                            "JSON repair produced no valid output for chunk %d (attempt %d)",
                            chunk_idx,
                            attempt,
                        )
                        continue
                    try:
                        chunk_result = IOutputData.model_validate_json(repaired)
                        logger.info(
                            "JSON repaired successfully for chunk %d", chunk_idx
                        )
                        break
                    except Exception as repair_err:
                        logger.warning(
                            "Repaired JSON still invalid (chunk %d, attempt %d): %s",
                            chunk_idx,
                            attempt,
                            repair_err,
                        )
                        continue

            except Exception as llm_err:
                logger.error(
                    "LLM invocation failed (chunk %d, attempt %d): %s",
                    chunk_idx,
                    attempt,
                    llm_err,
                )
                break  # don't retry on a hard LLM error

        if chunk_result is not None:
            logger.info(
                "Chunk %d/%d: %d medications, %d diseases, %d procedures",
                chunk_idx,
                total_chunks,
                len(chunk_result.medications),
                len(chunk_result.diseases),
                len(chunk_result.procedures),
            )
            chunk_results.append(chunk_result)
        else:
            logger.error(
                "Chunk %d/%d produced no usable result — entities in this section may be missing",
                chunk_idx,
                total_chunks,
            )

    if not chunk_results:
        logger.error("All chunks failed — no entities extracted")
        return IMedicalEntityExtractorAgentOutput(
            rund_id=payload.rund_id,
            status="failed",
            reason_code="processing_error",
            output=None,
        )

    result = _merge_outputs(chunk_results)

    logger.info(
        "Final merged totals: %d medications, %d diseases, %d procedures (from %d/%d chunks)",
        len(result.medications),
        len(result.diseases),
        len(result.procedures),
        len(chunk_results),
        total_chunks,
    )

    # ── Propagate NER metadata onto enriched entities ──────────
    if classified:
        _propagate_ner_metadata(result, classified)

    return IMedicalEntityExtractorAgentOutput(
        rund_id=payload.rund_id,
        status="completed",
        output=result,
    )
